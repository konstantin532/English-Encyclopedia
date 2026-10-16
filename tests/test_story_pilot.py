"""Пилот «курс через историю»: рамка истории, недели 3–4, связность, контрольный пакет."""
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.curriculum.models import Week, WeekScene
from apps.learning.models import WeekGoal

BEAT = """story_beat:
  intro_ru: "Утро. Анна впервые выходит на крыльцо нового дома."
  outcome_ru: "Анна и Том знакомятся."
  next_hook_ru: "Кто принесёт коробку?"
"""


@contextmanager
def content_copy(edit=None):
    """Временная копия content/; edit(root) меняет файлы перед загрузкой."""
    tmp = Path(tempfile.mkdtemp())
    try:
        root = tmp / "content"
        shutil.copytree(settings.CONTENT_DIR, root)
        if edit:
            edit(root)
        with override_settings(CONTENT_DIR=root):
            yield root
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def set_week1_beat(text: str):
    def edit(root: Path):
        path = root / "seed_weeks" / "a1_w01.yaml"
        body = path.read_text(encoding="utf-8")
        start = body.find("story_beat:")
        if start != -1:  # убрать прежнюю рамку до следующего ключа верхнего уровня
            rest = body[start:].split("\n")
            end = next((i for i, line in enumerate(rest[1:], 1) if line and not line.startswith(" ")), len(rest))
            body = body[:start] + "\n".join(rest[end:])
        path.write_text(body.rstrip("\n") + "\n" + text, encoding="utf-8")
    return edit


class StoryBeatTests(TestCase):
    def scene(self):
        return WeekScene.objects.get(week__level__code="A1", week__number=1)

    def test_loads_idempotently(self):
        with content_copy(set_week1_beat(BEAT)):
            call_command("load_content", verbosity=0)
            call_command("load_content", verbosity=0)
        self.assertEqual(WeekScene.objects.filter(week__level__code="A1", week__number=1).count(), 1)
        self.assertEqual(self.scene().story_beat["outcome_ru"], "Анна и Том знакомятся.")
        self.assertEqual(set(self.scene().story_beat), {"intro_ru", "outcome_ru", "next_hook_ru"})

    def test_missing_key_clears_old_beat(self):
        with content_copy(set_week1_beat(BEAT)):
            call_command("load_content", verbosity=0)
        with content_copy(set_week1_beat("")):
            call_command("load_content", verbosity=0)
        self.assertEqual(self.scene().story_beat, {})

    def test_goal_survives_reload(self):
        call_command("load_content", verbosity=0)
        user = User.objects.create_user("g@example.com", "s3cret-pass-123")
        week = Week.objects.get(level__code="A1", number=1)
        WeekGoal.objects.create(user=user, week=week, status="done")
        call_command("load_content", verbosity=0)
        self.assertEqual(WeekGoal.objects.get(user=user, week=week).status, "done")

    def test_html_is_escaped(self):
        with content_copy(set_week1_beat('story_beat:\n  intro_ru: "<script>alert(1)</script>"\n  outcome_ru: "Итог"\n')):
            call_command("load_content", verbosity=0)
        html = self.client.get(reverse("curriculum:week", args=["a1", 1])).content.decode()
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)", html)
        self.assertIn("Чем всё закончилось", html)

    def test_empty_beat_renders_nothing(self):
        with content_copy(set_week1_beat("")):
            call_command("load_content", verbosity=0)
        html = self.client.get(reverse("curriculum:week", args=["a1", 1])).content.decode()
        self.assertNotIn('id="story-intro"', html)
        self.assertNotIn("Чем всё закончилось", html)

    def test_week_five_stays_accessible(self):
        call_command("load_content", verbosity=0)
        self.assertEqual(self.client.get(reverse("curriculum:week", args=["a1", 5])).status_code, 200)

    def test_invalid_beat_rejected(self):
        bad = ['story_beat: "просто строка"\n',
               'story_beat:\n  intro_ru: "Да"\n  secret_ru: "Нет"\n',
               'story_beat:\n  intro_ru: 5\n']
        for text in bad:
            with self.subTest(text=text), content_copy(set_week1_beat(text)):
                with self.assertRaisesMessage(CommandError, "story_beat"):
                    call_command("load_content", verbosity=0)


from apps.stories.models import Story  # noqa: E402


class SpokenReminderTests(TestCase):
    """Живая речь: напоминание о spoken во всех неделях A1–A2 и во всех историях (правка плана 15.10.2026)."""

    @classmethod
    def setUpTestData(cls):
        call_command("load_content", verbosity=0)

    def warnings(self):
        from apps.publishing.audit import run_audit

        return run_audit().warnings

    def scene_with(self, text, week=5):
        w = Week.objects.get(level__code="A1", number=week)
        return WeekScene.objects.update_or_create(week=w, defaults=dict(
            can_do_ru="…", mission_ru="…", script=[{"speaker": "tom", "text": text}]))[0]

    def test_reminder_for_every_a1_week(self):
        self.scene_with("[T8]It[/] [D1]is[/] [T1]a[/] [S1]family[/] [S2]photo[/].")
        self.assertTrue([w for w in self.warnings() if "Неделя A1-5, реплика 1: можно сократить it is" in w])

    def test_reminder_for_every_story(self):
        story = Story.objects.get(number=2)
        story.script = [{"speaker": "anna", "text": "[T8]I[/] [D1]am[/] [S1]Anna[/].", "music": "calm"}]
        story.body, story.is_published = story.script[0]["text"], True
        story.save()
        self.assertTrue([w for w in self.warnings() if "История 2, реплика 1: можно сократить i am" in w])

    def test_new_forms_detected(self):
        self.scene_with("[T8]He[/] [D1]is[/] [N1]ten[/]. [T8]She[/] [D1]is[/] [J4]busy[/]. [A3]Here[/] [D1]is[/] [T3]your[/] "
                        "[S2]book[/]. [T9]What[/] [D1]is[/] [T3]your[/] [S9]name[/]? [T9]Who[/] [D1]is[/] [T2]this[/]? "
                        "[S1]Tom[/] [D1]does[/] [X1]not[/] [D3]like[/] [S3]coffee[/].")
        found = [w for w in self.warnings() if "Неделя A1-5, реплика 1: можно сократить" in w]
        self.assertTrue(found)
        for form in ("he is", "she is", "here is", "what is", "who is", "does not"):
            self.assertIn(form, found[0])

    def test_final_be_not_flagged(self):
        self.scene_with("[O4]Yes[/], [T8]he[/] [D1]is[/]. [A3]Here[/] [T8]you[/] [D1]are[/].")
        self.assertFalse([w for w in self.warnings() if "Неделя A1-5, реплика 1: можно сократить" in w])


from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit
from apps.curriculum.models import TongueTwister
from apps.publishing.audit import AuditReport
from apps.publishing.audit_weeks import audit_scene
from apps.stories.script import voices_manifest

STAGES = {"recognition", "substitution", "production", "transfer"}


def scene_errors(scene) -> list[str]:
    r = AuditReport()
    audit_scene(r, scene, voices_manifest())
    return r.errors


class WeekContentMixin:
    week_number = 0
    slugs: tuple[str, ...] = ()
    twister_number = 0

    @classmethod
    def setUpTestData(cls):
        call_command("load_content", verbosity=0)

    def check_complete(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=self.week_number)
        for order, slug in enumerate(self.slugs):
            lesson = Lesson.objects.get(slug=slug, is_published=True)
            self.assertEqual(lesson.week.number, self.week_number)
            self.assertEqual(set(lesson.layers.values_list("number", flat=True)), {1, 2, 3, 4, 5, 6, 7}, slug)
            self.assertEqual(set(lesson.exercises.values_list("stage", flat=True)), STAGES, slug)
        chunks = list(scene.chunks.all())
        self.assertTrue(5 <= len(chunks) <= 8)
        self.assertTrue(all(u.unit_type == "phrase" for u in chunks))
        self.assertEqual(TongueTwister.objects.get(week=scene.week).number, self.twister_number)
        self.assertEqual(scene_errors(scene), [])
        self.assertTrue(scene.story_beat.get("intro_ru") and scene.story_beat.get("outcome_ru"))

    def check_reload(self):
        counts = lambda: (LexicalUnit.objects.count(), Lesson.objects.count(), WeekScene.objects.count(),
                          TongueTwister.objects.count())
        before = counts()
        call_command("load_content", verbosity=0)
        self.assertEqual(counts(), before)


class WeekThreeTests(WeekContentMixin, TestCase):
    week_number, twister_number = 3, 3
    slugs = ("a1-cafe-order", "a1-numbers-1-20")

    def test_complete(self):
        self.check_complete()

    def test_reload_has_no_duplicates(self):
        self.check_reload()

    def test_lesson_order(self):
        self.assertEqual([Lesson.objects.get(slug=s).order for s in self.slugs], [5, 6])

    def test_repeat_request_taught_this_week(self):
        unit = LexicalUnit.objects.get(lemma="Sorry? Can you say it again, please?")
        self.assertEqual((unit.week.number, unit.unit_type), (3, "phrase"))

    def test_future_word_rejected(self):
        week4 = Week.objects.get(level__code="A1", number=4)
        first = LexicalUnit.objects.filter(week__number=1).first()
        LexicalUnit.objects.create(uid="LX-99990", lemma="zebrafish", meaning="test", part_of_speech=first.part_of_speech,
                                   semantic_class=first.semantic_class, internal_level=first.internal_level, week=week4,
                                   translation_ru="тест", example_en="[S6]zebrafish[/]")
        scene = WeekScene.objects.get(week__level__code="A1", week__number=3)
        self.assertEqual(scene_errors(scene), [])
        scene.script[0]["text"] += " [S6]zebrafish[/]"
        self.assertTrue([e for e in scene_errors(scene) if "zebrafish" in e])


from apps.poems.models import Poem
from apps.stories.models import Story


class WeekFourTests(WeekContentMixin, TestCase):
    week_number, twister_number = 4, 4
    slugs = ("a1-family-photo", "a1-family-possession")

    def test_complete(self):
        self.check_complete()

    def test_reload_has_no_duplicates(self):
        self.check_reload()

    def test_lesson_order(self):
        self.assertEqual([Lesson.objects.get(slug=s).order for s in self.slugs], [7, 8])

    def test_mystery_resolved_in_english(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=4)
        text = " ".join(line["text"] for line in scene.script)
        self.assertIn("[T3]my[/] [S2]photo[/]", text)  # Мия сама говорит по-английски, что это её фото
        self.assertTrue(any(line["speaker"] == "mia" for line in scene.script))
        self.assertNotIn("Rose", text)

    def test_course_slots_preserved(self):
        self.assertEqual({s.number: s.week.number for s in Story.objects.filter(number__in=[1, 2, 5])},
                         {1: 2, 2: 6, 5: 14})
        self.assertEqual((Story.objects.count(), Poem.objects.count()), (60, 60))

    def test_new_units_have_new_ids_and_unverified_cefr(self):
        new = LexicalUnit.objects.filter(uid__gte="LX-00055")
        self.assertGreater(new.count(), 40)
        self.assertEqual(new.count(), len(set(new.values_list("uid", flat=True))))
        self.assertEqual(set(new.values_list("cefr", flat=True)), {"unverified"})


class PilotContinuityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", verbosity=0)

    def test_four_weeks_have_framing(self):
        for n in range(1, 5):
            beat = WeekScene.objects.get(week__level__code="A1", week__number=n).story_beat
            with self.subTest(week=n):
                self.assertTrue(beat.get("intro_ru"))
                self.assertTrue(beat.get("outcome_ru"))

    def test_existing_canon_preserved(self):
        goals = {s.week.number: s.can_do_ru for s in WeekScene.objects.filter(week__number__in=[1, 2])}
        self.assertEqual(goals[1], "Я смогу представиться, сказать, откуда я, и спросить имя собеседника.")
        self.assertEqual(goals[2], "Я смогу показать свой дом, назвать вещи и вежливо попросить воды.")
        story = Story.objects.get(number=1)
        self.assertIn("[S6]cat[/]", story.script[-1]["text"])
        self.assertIn("Box", story.script[-1]["text"])

    def test_transfer_present(self):
        for lesson in Lesson.objects.filter(level__code="A1", week__number__lte=4):
            with self.subTest(slug=lesson.slug):
                self.assertTrue(lesson.exercises.filter(stage="transfer").exists())

    def test_wrong_answer_never_blocks_next_week(self):
        for n in range(1, 5):
            html = self.client.get(reverse("curriculum:week", args=["a1", n])).content.decode()
            self.assertIn(f'href="/levels/a1/weeks/{n + 1}/"', html)


import yaml as _yaml

from apps.curriculum.models import Level
from apps.publishing.audit import is_known, text_tokens, vocab_until
from apps.publishing.audit_weeks import audit_script, normalize_line
from apps.taxonomy.markup import find_issues

PACKAGE = Path(settings.BASE_DIR) / "docs" / "pilots" / "a1-four-weeks" / "assessment.yaml"


def package() -> dict:
    return _yaml.safe_load(PACKAGE.read_text(encoding="utf-8"))


def entry_problems(entry: dict) -> list[str]:
    """Незнакомые к max_week слова, ошибки разметки и реплик."""
    level = Level.objects.get(code="A1")
    vocab = vocab_until(level, entry["max_week"])
    problems = []
    for line in entry["script"]:
        for text in (line["text"], line.get("spoken", "")):
            problems += [f"{t}: незнакомое" for t in text_tokens(text) if not is_known(t, vocab)]
            problems += [f"{i.token}: {i.problem}" for i in find_issues(text)]
    r = AuditReport()
    audit_script(r, entry["id"], entry["script"], voices_manifest(), level=level, week_number=entry["max_week"])
    return problems + r.errors


class AssessmentPackageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", verbosity=0)

    def test_structure(self):
        data = package()
        self.assertEqual(data["level"], "A1")
        self.assertEqual([(e["id"], e["max_week"]) for e in data["weekly"]], [("w01", 1), ("w02", 2), ("w03", 3), ("w04", 4)])
        self.assertEqual([(e["id"], e["max_week"]) for e in data["forms"]], [("pre", 4), ("post", 4), ("delayed", 4)])
        for e in data["weekly"] + data["forms"]:
            with self.subTest(id=e["id"]):
                self.assertEqual(len(e["questions"]), 3)
                self.assertTrue(all(set(q) == {"prompt_ru", "accepted_ru"} and q["accepted_ru"] for q in e["questions"]))
                self.assertTrue(e["oral"]["prompt_ru"] and e["oral"]["cues_ru"])
                self.assertTrue(4 <= len(e["script"]) <= 8)

    def test_parallel_forms_are_unseen(self):
        data = package()
        norm = lambda script: tuple(normalize_line(l["text"]) for l in script)
        forms = [norm(e["script"]) for e in data["forms"]]
        self.assertEqual(len(set(forms)), 3)
        scenes = {normalize_line(l["text"]) for s in WeekScene.objects.all() for l in s.script}
        for e in data["weekly"] + data["forms"]:
            with self.subTest(id=e["id"]):
                overlap = set(norm(e["script"])) & scenes
                self.assertLessEqual(len(overlap), 1, overlap)  # не пересказ учебной сцены

    def test_weekly_vocab_boundary(self):
        for e in package()["weekly"] + package()["forms"]:
            with self.subTest(id=e["id"]):
                self.assertEqual(entry_problems(e), [])

    def test_future_word_fails(self):
        e = package()["weekly"][0]
        e["script"][0]["text"] += " [S1]brother[/]"  # brother вводится только на неделе 4
        self.assertTrue([p for p in entry_problems(e) if p.startswith("brother")])


from apps.drills.models import Exercise  # noqa: E402


class ReviewFixTests(TestCase):
    """Исправления по итоговому независимому ревью пилота."""

    @classmethod
    def setUpTestData(cls):
        call_command("load_content", verbosity=0)

    def test_commas_do_not_decide_answer(self):
        ex = Exercise(answer="Tea, please.", accepted=[])
        self.assertTrue(ex.is_correct("tea please"))
        self.assertTrue(ex.is_correct("Tea,please!"))
        self.assertFalse(ex.is_correct("Coffee, please."))

    def test_transfer_accepts_digits_and_thanks(self):
        cafe = Lesson.objects.get(slug="a1-cafe-order").exercises.get(stage="transfer")
        for answer in ("Tea, thanks.", "One tea please", "Can I have a tea please?"):
            self.assertTrue(cafe.is_correct(answer), answer)
        numbers = Lesson.objects.get(slug="a1-numbers-1-20").exercises.get(stage="transfer")
        self.assertTrue(numbers.is_correct("4 teas, please"))
        family = Lesson.objects.get(slug="a1-family-photo").exercises.get(stage="transfer")
        self.assertTrue(family.is_correct("This is my sister. She is 12."))

    def test_pronouns_have_no_be_forms(self):
        for lemma in ("he", "she"):
            self.assertEqual(LexicalUnit.objects.get(lemma=lemma).forms, [])

    def test_cafe_sells_cookies_not_whole_cakes(self):
        scene = WeekScene.objects.get(week__number=3)
        text = " ".join(l["text"] for l in scene.script)
        self.assertIn("cookie", text)
        self.assertNotIn("cake", text)
        self.assertFalse(LexicalUnit.objects.filter(lemma="cake").exists())

    def test_russian_frame_adds_no_facts(self):
        w3 = WeekScene.objects.get(week__number=3).story_beat
        w4 = WeekScene.objects.get(week__number=4).story_beat
        self.assertNotIn("на углу", w3["intro_ru"] + w3["outcome_ru"] + w4["outcome_ru"])
        self.assertNotIn("обронила", w4["outcome_ru"])
        self.assertNotIn("хозяина", w3["outcome_ru"])

    def test_numbers_lesson_describes_marker_correctly(self):
        body = Lesson.objects.get(slug="a1-numbers-1-20").layers.get(number=1).body
        self.assertNotIn("линия над словом", body)
        self.assertIn("Штриховая линия под словом", body)

    def test_forms_share_goals(self):
        """pre/post/delayed: заказ с числом → сбой «Sorry?» → кто на фото — одна схема."""
        for e in package()["forms"]:
            text = " ".join(l["text"] for l in e["script"])
            with self.subTest(id=e["id"]):
                self.assertIn("[N1]", text)
                self.assertIn("[O2]Sorry[/]?", text)
                self.assertTrue("[S2]photo[/]" in text or "[S1]family[/]" in text or "[T9]Who[/]" in text)

    def test_assessment_canon(self):
        w01 = " ".join(l["text"] for l in package()["weekly"][0]["script"])
        self.assertNotIn("[S1]neighbor[/]", w01)  # Мия не знакомится с Томом заново и не соседка
        w02 = " ".join(l["text"] for l in package()["weekly"][1]["script"])
        self.assertNotIn("[T3]'s[/]", w02)  # притяжательное 's учат только на неделе 4


class CanonTests(TestCase):
    """Согласование канона: Мия знакома с Анной с недели 2; кафе на углу — её работа."""

    @classmethod
    def setUpTestData(cls):
        call_command("load_content", verbosity=0)

    def test_story_two_does_not_reintroduce_mia(self):
        hook = Story.objects.get(number=2).hook_ru
        self.assertNotIn("знакомится", hook)
        self.assertIn("Ми", hook)

    def test_week_three_order_fits_two_people(self):
        scene = WeekScene.objects.get(week__number=3)
        order = scene.script[1]["text"]
        self.assertIn("[N1]One[/] [S3]coffee[/] [C1]and[/] [N1]one[/] [S3]tea[/]", order)

    def test_friends_use_ty_in_week_two(self):
        ru = " ".join(l.get("ru", "") for l in WeekScene.objects.get(week__number=2).script)
        self.assertNotIn("ваш телефон", ru)
        self.assertNotIn("ваша коробка", ru)


class BrokenManifestTests(TestCase):
    """Замечание P2 бота Codex в PR #4: повреждённый manifest.json не должен ронять загрузку курса."""

    def test_non_object_or_broken_manifest_is_skipped(self):
        for body in ("[]", '"corrupt"', "{not json", ""):
            tmp = Path(tempfile.mkdtemp())
            try:
                folder = tmp / "static" / "audio" / "weeks" / "a1-w01"
                folder.mkdir(parents=True)
                (folder / "manifest.json").write_text(body, encoding="utf-8")
                with self.subTest(body=body), override_settings(BASE_DIR=tmp):
                    call_command("load_content", verbosity=0)
                    self.assertEqual(WeekScene.objects.get(week__level__code="A1", week__number=1).audio, {})
            finally:
                shutil.rmtree(tmp, ignore_errors=True)


class WeekFiveTests(WeekContentMixin, TestCase):
    """Неделя 5 «Магазин у дома»: there is / are, some, How much…?, цены."""
    week_number = 5
    slugs = ("a1-there-is-some", "a1-how-much-prices")
    twister_number = 5

    def test_complete(self):
        self.check_complete()

    def test_page_shows_clerk_prices_and_twister(self):
        response = self.client.get(reverse("curriculum:week", args=["a1", 5]))
        self.assertContains(response, "Продавщица")
        self.assertContains(response, "How")
        self.assertContains(response, "dollars")
        self.assertContains(response, "eggs")

    def test_hook_leads_to_story_two(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=5)
        self.assertIn("Box", scene.story_beat["next_hook_ru"])
