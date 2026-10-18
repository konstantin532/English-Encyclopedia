import json
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape
from django.utils import timezone

from apps.accounts.models import User
from apps.curriculum.models import Level, Week
from apps.drills.models import Exercise
from apps.learning.models import Status, UnitProgress
from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit
from apps.taxonomy.models import PartOfSpeech, SemanticClass
from tests.runner import ensure_content


class SeedTests(TestCase):
    def test_registry_and_levels_seeded_by_migrate(self):
        self.assertEqual(PartOfSpeech.objects.count(), 11)
        self.assertEqual(SemanticClass.objects.filter(category__code="S").count(), 10)
        self.assertEqual(Level.objects.count(), 8)
        self.assertEqual(Week.objects.count(), 150)

    def test_class_color_follows_number(self):
        cls = SemanticClass.objects.get(category__code="D", number=3)
        self.assertEqual(cls.color, "#b98a00")
        self.assertEqual(cls.class_id, "D3")


class ContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_packages_loaded(self):
        self.assertEqual(LexicalUnit.objects.filter(internal_level__code="A1").count(), 500)
        self.assertEqual(Lesson.objects.filter(level__code="A1").count(), 28)
        for slug in ["a1-verb-be", "a1-determiners-a-the-this-my", "a1-have-like-can-do"]:
            lesson = Lesson.objects.get(slug=slug)
            self.assertEqual(lesson.layers.count(), 7, slug)
            self.assertEqual(lesson.exercises.count(), 5 if slug == "a1-verb-be" else 6, slug)
        lesson = Lesson.objects.get(slug="a1-nouns-first-words")
        self.assertEqual(lesson.layers.count(), 7)
        self.assertEqual(lesson.exercises.count(), 4)
        self.assertEqual(lesson.units.count(), 15)

    def test_loader_is_idempotent(self):
        call_command("load_content", verbosity=0)
        self.assertEqual(LexicalUnit.objects.count(), 500)

    def test_cefr_only_with_source(self):
        for u in LexicalUnit.objects.exclude(cefr="unverified"):
            self.assertNotEqual(u.verification_status, "pending", u.uid)
            self.assertIn("Oxford 3000", u.verification_note, u.uid)

    def test_uids_unique_and_well_formed(self):
        uids = list(LexicalUnit.objects.values_list("uid", flat=True))
        self.assertEqual(len(uids), len(set(uids)))
        self.assertTrue(all(u.startswith("LX-") and len(u) == 8 for u in uids))

    def test_pages_render(self):
        for url in ["/", "/markers/", "/words/", "/words/LX-00008/", "/levels/a1/", "/levels/b2-plus/",
                    "/lessons/a1-nouns-first-words/", "/accounts/signup/", "/accounts/login/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_lesson_html_does_not_leak_answers(self):
        html = self.client.get("/lessons/a1-nouns-first-words/").content.decode()
        self.assertNotIn("My name is Anna", html.split('id="practice"')[1])

    def test_audit_has_no_errors(self):
        from apps.publishing.audit import run_audit

        self.assertEqual(run_audit().errors, [])

    def test_every_english_word_shown_to_learner_is_registered(self):
        from apps.publishing.audit import run_audit

        self.assertEqual(run_audit().unknown_words, {})

    def test_forms_and_contractions_count_as_known(self):
        from apps.publishing.audit import is_known, known_vocabulary

        vocab = known_vocabulary()
        for word in ["am", "is", "I'm", "it's", "isn't", "don't", "an", "books", "Anna"]:
            self.assertTrue(is_known(word, vocab), word)
        self.assertFalse(is_known("elephant", vocab))

    def test_audit_rejects_unsplit_negative_contractions(self):
        from apps.publishing.audit import run_audit

        unit = LexicalUnit.objects.get(uid="LX-00016")
        for text in ["[D1]isn't[/]", "[D1]aren't[/]", "[D1]don't[/]", "[D7]can't[/]"]:
            with self.subTest(text=text):
                unit.example_en = text
                unit.save()
                self.assertTrue(any("слитная форма" in e and text in e for e in run_audit().errors))
        unit.example_en = "[T8]It[/] [D1]is[/][X1]n't[/]."
        unit.save()
        self.assertEqual(run_audit().errors, [])

    def test_sound_notes_loaded_and_rendered_after_layer_five(self):
        for lesson in Lesson.objects.all():
            with self.subTest(slug=lesson.slug):
                self.assertEqual(len(lesson.sound_notes), 3)
                response = self.client.get(f"/lessons/{lesson.slug}/")
                html = response.content.decode()
                self.assertIn('href="#sound-notes"', html)
                self.assertLess(html.index('id="layer-5"'), html.index('id="sound-notes"'))
                self.assertLess(html.index('id="sound-notes"'), html.index('id="layer-6"'))
                for item in lesson.sound_notes:
                    self.assertContains(response, f'<span lang="en">{escape(item["text"])}</span>', html=True)
                    self.assertIn('<span class="ipa">' + item["ipa"] + '</span>', html)
                    self.assertIn(escape(item["note_ru"]), html)

    def test_sound_notes_vocabulary_is_audited(self):
        from apps.publishing.audit import run_audit

        lesson = Lesson.objects.get(slug="a1-verb-be")
        lesson.sound_notes = [{"text": "elephant", "ipa": "/test/", "note_ru": "test"}]
        lesson.save()
        self.assertIn("elephant", run_audit().unknown_words)

    def test_new_lessons_render(self):
        for slug in ["a1-verb-be", "a1-determiners-a-the-this-my", "a1-have-like-can-do"]:
            self.assertEqual(self.client.get(f"/lessons/{slug}/").status_code, 200, slug)

    def test_word_search_by_english_and_russian_respects_filters(self):
        for query in ["home", "дом"]:
            response = self.client.get("/words/", {"q": query, "level": "A1", "cat": "S"})
            self.assertEqual(response.status_code, 200)
            self.assertIn("home", [unit.lemma for unit in response.context["units"]])
        response = self.client.get("/words/", {"q": "home", "cat": "D"})
        self.assertNotIn("home", [unit.lemma for unit in response.context["units"]])
        self.assertTrue(all(unit.part_of_speech.code == "D" for unit in response.context["units"]))
        response = self.client.get("/words/", {"q": '<script>alert("test")</script>'})
        self.assertNotContains(response, '<script>alert("test")</script>')


class ExerciseApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.ex = Exercise.objects.get(lesson__slug="a1-nouns-first-words", order=3)

    def post(self, data):
        return self.client.post(reverse("api:check_exercise", args=[self.ex.pk]), json.dumps(data),
                                content_type="application/json").json()

    def test_wrong_answer_does_not_reveal(self):
        data = self.post({"answer": "Name my is Anna"})
        self.assertFalse(data["correct"])
        self.assertNotIn("answer", data)

    def test_correct_answer_is_normalized(self):
        self.assertTrue(self.post({"answer": "my  name is anna."})["correct"])

    def test_reveal_on_request(self):
        self.assertEqual(self.post({"reveal": True})["answer"], "My name is Anna")

    def test_progress_saved_for_logged_in_user(self):
        user = User.objects.create_user("anna@example.com", "s3cret-pass-123")
        self.client.force_login(user)
        self.post({"answer": "My name is Anna"})
        p = UnitProgress.objects.get(user=user, unit__uid="LX-00015")
        self.assertEqual(p.status, Status.RECOGNITION)
        self.assertGreater(p.next_review_at, timezone.now() + timedelta(hours=23))


class ProgressRuleTests(TestCase):
    def setUp(self):
        ensure_content()
        self.user = User.objects.create_user("t@example.com", "s3cret-pass-123")
        self.p = UnitProgress.objects.create(user=self.user, unit=LexicalUnit.objects.first())

    def test_active_requires_three_different_constructions(self):
        for _ in range(6):
            self.p.register(True, "same-context")
        self.assertEqual(self.p.status, Status.INDEPENDENT_USE)
        self.p.register(True, "ctx-2")
        self.p.register(True, "ctx-3")
        self.assertEqual(self.p.status, Status.ACTIVE)

    def test_mistake_shortens_interval(self):
        self.p.register(True, "a")
        self.p.register(True, "b")
        stage = self.p.stage
        self.p.register(False)
        self.assertEqual(self.p.stage, stage - 1)


class AccountTests(TestCase):
    def test_signup_errors_keep_form_and_do_not_create_account(self):
        response = self.client.post("/accounts/signup/", {
            "email": "studio@example.com", "display_name": "Анна",
            "password1": "studio-test-password-123", "password2": "different-password-123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertContains(response, 'name="password2"')
        self.assertContains(response, 'href="/accounts/login/"')
        self.assertFalse(User.objects.filter(email="studio@example.com").exists())

    def test_login_and_logout_keep_csrf_protection_and_next_destination(self):
        from django.test import Client

        User.objects.create_user("studio@example.com", "studio-test-password-123")
        client = Client(enforce_csrf_checks=True)
        client.get("/accounts/login/?next=/learning/review/")
        self.assertEqual(client.post("/accounts/login/", {
            "username": "studio@example.com", "password": "studio-test-password-123",
        }).status_code, 403)
        response = client.post("/accounts/login/", {
            "username": "studio@example.com", "password": "studio-test-password-123",
            "next": "/learning/review/", "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, "/learning/review/")
        self.assertContains(client.get("/learning/"), "Мой кабинет")
        self.assertEqual(client.get("/accounts/logout/").status_code, 405)
        self.assertEqual(client.post("/accounts/logout/").status_code, 403)
        response = client.post("/accounts/logout/", {
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.get("/learning/").status_code, 302)

    def test_signup_logs_in_and_redirects(self):
        r = self.client.post("/accounts/signup/", {"email": "New@Example.com", "display_name": "Костя",
                                                   "password1": "very-long-pass-77", "password2": "very-long-pass-77"})
        self.assertRedirects(r, "/learning/")
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_dashboard_requires_login(self):
        self.assertEqual(self.client.get("/learning/").status_code, 302)

    def test_email_case_insensitive_login_and_no_duplicates(self):
        User.objects.create_user("Mia@Example.com", "very-long-pass-77")
        self.assertTrue(self.client.login(username="mia@example.com", password="very-long-pass-77"))
        r = self.client.post("/accounts/login/", {"username": "MIA@example.com", "password": "very-long-pass-77"})
        self.assertEqual(r.status_code, 302)
        self.client.logout()
        r = self.client.post("/accounts/signup/", {"email": "MIA@EXAMPLE.COM", "display_name": "",
                                                   "password1": "very-long-pass-77", "password2": "very-long-pass-77"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.count(), 1)


class CsrfFlowTests(TestCase):
    """Гость открывает урок и проверяет ответ с настоящей CSRF-защитой, как в браузере."""

    def test_guest_can_check_answer_with_csrf(self):
        from django.test import Client

        call_command("load_content", verbosity=0)
        c = Client(enforce_csrf_checks=True)
        c.get("/lessons/a1-nouns-first-words/")
        token = c.cookies["csrftoken"].value
        ex = Exercise.objects.get(lesson__slug="a1-nouns-first-words", order=1)
        r = c.post(reverse("api:check_exercise", args=[ex.pk]), json.dumps({"answer": "phone"}),
                   content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["correct"])


class ReviewTests(TestCase):
    def setUp(self):
        ensure_content()
        self.user = User.objects.create_user("r@example.com", "very-long-pass-77")
        self.client.force_login(self.user)

    def make_due(self, uid):
        unit = LexicalUnit.objects.get(uid=uid)
        return UnitProgress.objects.create(user=self.user, unit=unit, status=Status.RECOGNITION,
                                           next_review_at=timezone.now() - timedelta(minutes=1))

    def test_empty_review_page(self):
        r = self.client.get("/learning/review/")
        self.assertContains(r, "Сейчас повторять нечего")

    def test_due_unit_gets_unsolved_exercise_then_recall_card(self):
        self.make_due("LX-00015")  # name — есть упражнение в уроке 1
        r = self.client.get("/learning/review/")
        self.assertContains(r, "Меня зовут Анна")
        ex = Exercise.objects.get(lesson__slug="a1-nouns-first-words", order=3)
        self.client.post(reverse("api:check_exercise", args=[ex.pk]), json.dumps({"answer": "My name is Anna"}),
                         content_type="application/json")
        UnitProgress.objects.filter(unit__uid="LX-00015").update(next_review_at=timezone.now() - timedelta(minutes=1))
        r = self.client.get("/learning/review/")
        self.assertContains(r, "Как по-английски «имя, название»?")

    def test_recall_checks_lemma_and_forms_and_reschedules(self):
        p = self.make_due("LX-00016")  # be
        url = reverse("api:recall_unit", args=["LX-00016"])
        self.assertTrue(self.client.post(url, json.dumps({"answer": "is"}), content_type="application/json").json()["correct"])
        p.refresh_from_db()
        self.assertGreater(p.next_review_at, timezone.now())
        self.assertEqual(p.contexts_used, [])  # вспоминание не считается новой конструкцией
        wrong = self.client.post(url, json.dumps({"answer": "do"}), content_type="application/json").json()
        self.assertFalse(wrong["correct"])
        self.assertNotIn("answer", wrong)

    def test_header_shows_due_count(self):
        self.make_due("LX-00001")
        self.make_due("LX-00002")
        self.assertContains(self.client.get("/"), '<span class="badge">2</span>')


class StoriesPoemsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_course_map_complete(self):
        from apps.poems.models import Poem
        from apps.stories.models import Story

        self.assertEqual(Story.objects.count(), 60)
        self.assertEqual(Poem.objects.count(), 60)
        self.assertEqual(Story.objects.filter(level__code="B1").count(), 10)
        self.assertEqual(Poem.objects.filter(level__code="B2+").count(), 8)

    def test_story_and_poem_pass_audit(self):
        from apps.publishing.audit import run_audit

        report = run_audit()
        self.assertEqual(report.errors, [])
        self.assertTrue(any("История 1:" in f and "знакомых" in f for f in report.facts))

    def test_pages(self):
        self.assertContains(self.client.get("/stories/"), "Not My Box")
        r = self.client.get("/stories/1/")
        self.assertContains(r, 'data-cat="S" data-cls="6"')
        self.assertContains(self.client.get("/stories/poems/1/"), "/aɪ hæv maɪ ˈfoʊn/")
        self.assertEqual(self.client.get("/stories/6/").status_code, 404)  # ещё не написана

    def test_poem_gap_check_hides_answer_until_attempt(self):
        url = reverse("api:check_poem_gap", args=[1, 0])
        wrong = self.client.post(url, json.dumps({"answer": "book"}), content_type="application/json").json()
        self.assertEqual(wrong, {"correct": False})
        self.assertTrue(self.client.post(url, json.dumps({"answer": "Phone"}), content_type="application/json").json()["correct"])


class ReviewFixesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_search_cyrillic_any_case_and_forms(self):
        for q in ["дом", "Дом", "ДОМ"]:
            r = self.client.get("/words/", {"q": q})
            self.assertContains(r, "LX-00005", msg_prefix=q)  # home — дом
        self.assertContains(self.client.get("/words/", {"q": "Is"}), "LX-00016")  # форма be

    def test_search_count_is_declined(self):
        from apps.core.templatetags.ru import plural_ru

        forms = "учебная единица,учебные единицы,учебных единиц"
        self.assertEqual(plural_ru(1, forms), "1 учебная единица")
        self.assertEqual(plural_ru(3, forms), "3 учебные единицы")
        self.assertEqual(plural_ru(11, forms), "11 учебных единиц")
        self.assertEqual(plural_ru(22, forms), "22 учебные единицы")
        html = self.client.get("/words/", {"q": "home"}).content.decode()
        self.assertRegex(html, r"\b([2-4]|2[2-4]) учебные единицы по запросу «home»")

    def test_substitutions_use_only_learned_words(self):
        from apps.publishing.audit import run_audit

        self.assertFalse([e for e in run_audit().errors if "подстановка" in e])

    def test_header_has_visible_marker_toggle_label(self):
        self.assertContains(self.client.get("/"), 'class="toggle-short"')


class StoryVoicesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_body_is_built_from_script_by_roles(self):
        from apps.stories.models import Story

        story = Story.objects.get(number=1)
        self.assertEqual(len(story.script), 10)
        self.assertEqual({l["speaker"] for l in story.script}, {"anna", "tom"})
        self.assertEqual(story.body.count("\n\n"), 9)
        self.assertEqual(story.ambience, "morning_home")

    def test_story_page_shows_speakers(self):
        r = self.client.get("/stories/1/")
        self.assertContains(r, 'data-speaker="tom"')
        self.assertContains(r, ">Том<")

    def test_every_role_has_a_distinct_voice(self):
        import yaml
        from django.conf import settings

        data = yaml.safe_load((settings.CONTENT_DIR / "manifests" / "voices.yaml").read_text(encoding="utf-8"))
        voices = [r["voice"] for r in data["roles"].values()]
        self.assertEqual(len(voices), len(set(voices)))
        self.assertFalse(set(voices) & set(data["extras"]))
