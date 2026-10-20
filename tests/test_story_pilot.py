"""Пилот «курс через историю»: рамка истории, недели 3–4, связность, контрольный пакет."""
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.test import tag
from django.urls import reverse

from apps.accounts.models import User
from apps.curriculum.models import Week, WeekScene
from apps.learning.models import WeekGoal
from tests.runner import ensure_content

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


@tag("slow")  # намеренно ломает и перезагружает весь курс; полный прогон — перед слиянием
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
        ensure_content()

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
        ensure_content()

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

    def test_polite_order_and_want(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=3)
        text = " ".join(line["text"] for line in scene.script)
        spoken = " ".join(line.get("spoken", "") for line in scene.script)
        self.assertIn("[T9]What[/] [D7]would[/] [T8]you[/] [D3]like[/]?", text)
        self.assertIn("[T8]I[/][D7]'d[/] [D3]like[/]", spoken)
        self.assertIn("[D3]want[/]", text)

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

    def test_age_and_plural_pronouns(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=4)
        text = " ".join(line["text"] for line in scene.script)
        for piece in ("[A6]How[/] [J2]old[/] [D1]are[/] [T8]they[/]", "[T8]We[/]", "[S1]mom[/]", "[N5]forty[/]"):
            self.assertIn(piece, text)

    def test_course_slots_preserved(self):
        self.assertEqual({s.number: s.week.number for s in Story.objects.filter(number__in=[1, 2, 5])},
                         {1: 2, 2: 6, 5: 14})
        self.assertEqual((Story.objects.count(), Poem.objects.count()), (60, 60))

    def test_new_units_have_new_ids_and_evidence_based_cefr(self):
        new = LexicalUnit.objects.filter(uid__gte="LX-00055")
        self.assertGreater(new.count(), 40)
        self.assertEqual(new.count(), len(set(new.values_list("uid", flat=True))))
        # Do not require future source-backed entries to remain unverified forever.
        sourced = new.exclude(cefr="unverified")
        self.assertEqual(set(sourced.values_list("uid", flat=True)), {"LX-00113", "LX-00303"})
        for entry in sourced:
            self.assertEqual(entry.verification_status, "verified")
            self.assertIn("Cambridge English Dictionary", entry.verification_note)
        self.assertEqual(new.filter(cefr="unverified", verification_status="pending").count(),
                         new.count() - sourced.count())


class PilotContinuityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_four_weeks_have_framing(self):
        for n in range(1, 5):
            beat = WeekScene.objects.get(week__level__code="A1", week__number=n).story_beat
            with self.subTest(week=n):
                self.assertTrue(beat.get("intro_ru"))
                self.assertTrue(beat.get("outcome_ru"))

    def test_existing_canon_preserved(self):
        goals = {s.week.number: s.can_do_ru for s in WeekScene.objects.filter(week__number__in=[1, 2])}
        self.assertEqual(goals[1], "Я смогу представиться, сказать, откуда я, и спросить имя собеседника.")
        self.assertEqual(goals[2], "Я смогу показать свой дом, назвать комнаты и предметы, сказать, чьи они, и вежливо попросить воды или нужную вещь.")
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
        ensure_content()

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
        ensure_content()

    def test_commas_do_not_decide_answer(self):
        ex = Exercise(answer="Tea, please.", accepted=[])
        self.assertTrue(ex.is_correct("tea please"))
        self.assertTrue(ex.is_correct("Tea,please!"))
        self.assertFalse(ex.is_correct("Coffee, please."))

    def test_transfer_accepts_digits_and_thanks(self):
        cafe = Lesson.objects.get(slug="a1-cafe-order").exercises.get(order=4)
        for answer in ("Tea, thanks.", "One tea please", "Can I have a tea please?"):
            self.assertTrue(cafe.is_correct(answer), answer)
        numbers = Lesson.objects.get(slug="a1-numbers-1-20").exercises.get(stage="transfer")
        self.assertTrue(numbers.is_correct("4 teas, please"))
        family = Lesson.objects.get(slug="a1-family-photo").exercises.get(order=4)
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
        ensure_content()

    def test_story_two_does_not_reintroduce_mia(self):
        hook = Story.objects.get(number=2).hook_ru
        self.assertNotIn("знакомится", hook)
        self.assertIn("Ми", hook)

    def test_week_three_order_fits_two_people(self):
        scene = WeekScene.objects.get(week__number=3)
        order = scene.script[1]["text"]
        self.assertIn("[n1]one[/] [s3]coffee[/] [c1]and[/] [n1]one[/] [s3]tea[/]", order.lower())

    def test_friends_use_ty_in_week_two(self):
        ru = " ".join(l.get("ru", "") for l in WeekScene.objects.get(week__number=2).script)
        self.assertNotIn("ваш телефон", ru)
        self.assertNotIn("ваша коробка", ru)


@tag("slow")  # намеренно ломает и перезагружает весь курс; полный прогон — перед слиянием
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

    def test_colors_and_price_words_in_dialogue(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=5)
        text = " ".join(line["text"] for line in scene.script)
        for piece in ("[J2]red[/] [S3]apples[/]", "[J3]cheap[/]", "[J3]expensive[/]"):
            self.assertIn(piece, text)
    twister_number = 5

    def test_complete(self):
        self.check_complete()

    def test_page_shows_clerk_prices_and_twister(self):
        response = self.client.get(reverse("curriculum:week", args=["a1", 5]))
        self.assertContains(response, "Продавщица")
        self.assertContains(response, "How")
        self.assertContains(response, "dollars")
        self.assertContains(response, "cheese")  # скороговорка недели: cheese / cheap против milk / is

    def test_hook_leads_to_story_two(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=5)
        self.assertIn("Box", scene.story_beat["next_hook_ru"])


class WeekSixTests(WeekContentMixin, TestCase):
    """Неделя 6 «Мой обычный день»: Present Simple с I / you, время at seven."""
    week_number = 6
    slugs = ("a1-present-simple-i-you", "a1-time-at-seven")

    def test_daily_routine_words_in_dialogue(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=6)
        text = " ".join(line["text"] for line in scene.script)
        for piece in ("[D4]go[/] [P2]to[/] [S2]bed[/] [A2]early[/]", "[D2]eat[/]"):
            self.assertIn(piece, text)
    twister_number = 6

    def test_complete(self):
        self.check_complete()

    def test_hook_leads_to_story_two(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=6)
        self.assertIn("в семь", scene.story_beat["next_hook_ru"])


class StoryTwoTests(TestCase):
    """История 2 «The Café on the Corner»: Box находится в кафе и сам возвращается домой."""

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_story_two_published_at_week_six(self):
        story = Story.objects.get(number=2)
        self.assertTrue(story.is_published)
        self.assertEqual(story.week.number, 6)
        self.assertEqual(story.script[0]["music"], "morning")
        self.assertEqual(list(story.new_units.values_list("uid", flat=True)), ["LX-00141"])

    def test_story_two_page_renders(self):
        response = self.client.get(reverse("stories:detail", args=[2]))
        self.assertContains(response, "corner")
        self.assertContains(response, "Мия")


class WeekSevenTests(WeekContentMixin, TestCase):
    """Неделя 7 «Кто где работает»: he / she works, профессии, сосед сверху."""
    week_number = 7
    slugs = ("a1-he-she-works", "a1-jobs-what-do-you-do")

    def test_work_schedule_in_dialogue(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=7)
        text = " ".join(line["text"] for line in scene.script)
        for piece in ("[A6]Where[/] [D1]do[/] [T8]you[/] [D2]work[/]?", "[D8]start[/]", "[D8]finish[/]"):
            self.assertIn(piece, text)
    twister_number = 7

    def test_complete(self):
        self.check_complete()

    def test_third_person_s_in_dialogue(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=7)
        text = " ".join(line["text"] for line in scene.script)
        self.assertGreaterEqual(text.count("[D2]works[/]"), 3)

    def test_hook_leads_to_story_three(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=7)
        self.assertIn("под дверью", scene.story_beat["next_hook_ru"])


class WeekEightTests(WeekContentMixin, TestCase):
    """Неделя 8 «Как пройти?»: Where is…?, предлоги места, указания."""
    week_number = 8
    slugs = ("a1-where-is-prepositions", "a1-directions-turn-left")

    def test_help_us_and_between_in_dialogue(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=8)
        text = " ".join(line["text"] for line in scene.script)
        for piece in ("[D2]help[/] [T8]us[/]", "[P1]between[/]"):
            self.assertIn(piece, text)
    twister_number = 8

    def test_complete(self):
        self.check_complete()

    def test_on_is_a_word_not_a_boolean(self):
        from apps.lexicon.models import LexicalUnit

        self.assertEqual(LexicalUnit.objects.get(uid="LX-00172").lemma, "on")


class StoryThreeTests(TestCase):
    """История 3 «Whose Key?»: ключ подходит к старому почтовому ящику."""

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_story_three_published_at_week_eight(self):
        story = Story.objects.get(number=3)
        self.assertTrue(story.is_published)
        self.assertEqual(story.week.number, 8)
        self.assertEqual(story.script[0]["music"], "mystery")
        self.assertEqual(story.new_units.count(), 3)

    def test_story_three_page_renders(self):
        response = self.client.get(reverse("stories:detail", args=[3]))
        self.assertContains(response, "mailbox")


class WeekNineTests(WeekContentMixin, TestCase):
    """Неделя 9 «Телефон и сообщения»: do / does, диктовка по буквам и цифрам."""
    week_number = 9
    slugs = ("a1-questions-do-does", "a1-spelling-phone-numbers")

    def test_phone_closing_in_dialogue(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=9)
        text = " ".join(line["text"] for line in scene.script)
        for piece in ("[D2]closes[/]", "[A2]tomorrow[/]", "[O1]Bye[/]"):
            self.assertIn(piece, text)
    twister_number = 9

    def test_complete(self):
        self.check_complete()

    def test_spelled_surname_is_known(self):
        from apps.publishing.audit import character_names

        self.assertIn("belova", character_names())

    def test_continuity_copy_is_made_in_week_nine(self):
        week8 = WeekScene.objects.get(week__level__code="A1", week__number=8)
        week9 = WeekScene.objects.get(week__level__code="A1", week__number=9)
        self.assertIn("обещает сделать копию", week8.story_beat["outcome_ru"])
        self.assertIn("почти готова", week9.story_beat["intro_ru"])


class WeekTenTests(WeekContentMixin, TestCase):
    """Неделя 10 «Выходные и хобби»: always / never, like + -ing."""
    week_number = 10
    slugs = ("a1-always-never", "a1-like-doing")
    twister_number = 10

    def test_complete(self):
        self.check_complete()

    def test_calendar_and_clothes_in_dialogue(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=10)
        text = " ".join(line["text"] for line in scene.script)
        for marked in ("[S7]October[/]", "[S7]Friday[/]", "[S2]jacket[/]"):
            self.assertIn(marked, text)

    def test_calendar_and_clothes_are_practised(self):
        for slug in self.slugs:
            lesson = Lesson.objects.get(slug=slug)
            self.assertEqual(list(lesson.exercises.order_by("order").values_list("order", flat=True)), [1, 2, 3, 4, 5, 6])
        calendar = Lesson.objects.get(slug=self.slugs[0])
        for name in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                     "January", "February", "March", "April", "May", "June", "July",
                     "August", "September", "October", "November", "December"):
            self.assertTrue(calendar.units.filter(lemma=name).exists(), name)
        clothes = Lesson.objects.get(slug=self.slugs[1])
        self.assertEqual(set(clothes.units.filter(lemma__in=("shirt", "jacket", "shoes")).values_list("lemma", flat=True)), {"shirt", "jacket", "shoes"})

    def test_mia_still_works_every_day(self):
        """Канон недели 6: Мия работает каждый день — значит, и в воскресенье."""
        scene = WeekScene.objects.get(week__level__code="A1", week__number=10)
        mia = " ".join(line["text"] for line in scene.script if line["speaker"] == "mia")
        self.assertNotIn("[A1]never[/] [D2]work[/]", mia)
        self.assertIn("[D2]work[/] [P3]on[/] [S7]Sundays[/]", mia)
        self.assertIn("[A1]always[/] [D8]start[/] [P3]at[/] [N3]five[/]", mia)


class WeekElevenTests(WeekContentMixin, TestCase):
    """Неделя 11 «У врача»: headache, hurts, can't / cannot."""
    week_number = 11
    slugs = ("a1-what-hurts", "a1-cant-cannot")
    twister_number = 11

    def test_complete(self):
        self.check_complete()

    def test_new_health_words_in_dialogue(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=11)
        text = " ".join(line["text"] for line in scene.script)
        for marked in ("[D3]feel[/]", "[J4]sick[/]", "[J4]tired[/]", "[D2]rest[/]"):
            self.assertIn(marked.casefold(), text.casefold())

    def test_body_and_feeling_words_are_taught_with_six_exercises(self):
        pain = Lesson.objects.get(slug=self.slugs[0])
        for lemma in ("body", "face", "eye", "ear", "nose", "mouth", "tooth", "neck",
                      "arm", "hand", "finger", "leg", "foot", "pain"):
            self.assertTrue(pain.units.filter(lemma=lemma).exists(), lemma)
        ability = Lesson.objects.get(slug=self.slugs[1])
        for lemma in ("sick", "tired", "hungry", "thirsty", "well", "medicine", "rest", "sit", "feel"):
            self.assertTrue(ability.units.filter(lemma=lemma).exists(), lemma)
        for lesson in (pain, ability):
            self.assertEqual(list(lesson.exercises.order_by("order").values_list("order", flat=True)), [1, 2, 3, 4, 5, 6])
        self.assertIn("teeth", LexicalUnit.objects.get(lemma="tooth").forms)
        self.assertIn("feet", LexicalUnit.objects.get(lemma="foot").forms)

    def test_cant_is_split_into_base_and_negation(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=11)
        spoken = " ".join(line.get("spoken", "") for line in scene.script)
        self.assertIn("[D7]ca[/][X1]n't[/]", spoken)
        self.assertNotIn("[D7]can't[/]", spoken)


class WeekTwelveTests(WeekContentMixin, TestCase):
    """Неделя 12 «На почте»: don't / doesn't, письмо и адрес."""
    week_number = 12
    slugs = ("a1-dont-doesnt", "a1-letters-address")
    twister_number = 12

    def test_complete(self):
        self.check_complete()

    def test_postal_worker_says_old_mailbox_gets_no_letters(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=12)
        text = " ".join(line["text"] for line in scene.script if line["speaker"] == "postal")
        self.assertIn("[D1]does[/] [X1]not[/] [D2]get[/] [S9]letters[/]", text)


class StoryFourTests(TestCase):
    """История 4 «A Letter With No Name»: письмо, которое не принесла почта."""

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_story_four_published_at_week_twelve(self):
        story = Story.objects.get(number=4)
        self.assertTrue(story.is_published)
        self.assertEqual(story.week.number, 12)
        self.assertIn("[S1]Rose[/]", story.body)
        self.assertEqual(story.new_units.count(), 2)

    def test_rose_is_a_character_not_vocabulary(self):
        from apps.publishing.audit import character_names

        self.assertIn("rose", character_names())

    def test_week_eleven_leads_to_post_office_not_to_letter(self):
        week11 = WeekScene.objects.get(week__level__code="A1", week__number=11)
        self.assertIn("почту", week11.story_beat["next_hook_ru"])


class WeekThirteenTests(WeekContentMixin, TestCase):
    """Неделя 13 «Курсы английского»: can / can't — умения, Why? Because…"""
    week_number = 13
    slugs = ("a1-can-skills", "a1-why-because")
    twister_number = 13

    def test_complete(self):
        self.check_complete()

    def test_anna_speaks_russian_by_canon(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=13)
        anna = " ".join(line["text"] for line in scene.script if line["speaker"] == "anna")
        self.assertIn("[S4]Russia[/]", anna)

    def test_hook_leads_to_story_five(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=13)
        self.assertIn("шкаф", scene.story_beat["next_hook_ru"])


class WeekFourteenTests(WeekContentMixin, TestCase):
    """Неделя 14 «Поездка на автобусе»: билет, расписание и итог A1."""
    week_number = 14
    slugs = ("a1-bus-ticket", "a1-review-everything")
    twister_number = 14

    def test_complete(self):
        self.check_complete()


class StoryFiveTests(TestCase):
    """История 5 «The Big Family Photo»: фото за шкафом, Rose и Park Street."""

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_story_five_published_at_week_fourteen(self):
        story = Story.objects.get(number=5)
        self.assertTrue(story.is_published)
        self.assertEqual(story.week.number, 14)
        self.assertIn("[S1]Rose[/]", story.body)
        self.assertIn("[S4]Park[/] [S4]Street[/]", story.body)


class LevelA1CompleteTests(TestCase):
    """Все 14 недель A1 наполнены: сцена, два урока, скороговорка; все 5 историй A1 опубликованы."""

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_every_a1_week_has_scene_lessons_and_twister(self):
        from apps.curriculum.models import TongueTwister

        for number in range(1, 15):
            scene = WeekScene.objects.get(week__level__code="A1", week__number=number)
            self.assertGreaterEqual(scene.week.lessons.count(), 2, number)
            self.assertTrue(TongueTwister.objects.filter(week=scene.week).exists(), number)

    def test_all_a1_stories_published(self):
        published = Story.objects.filter(level__code="A1", is_published=True).count()
        self.assertEqual(published, 5)


class TwisterMethodTests(TestCase):
    """Скороговорка по методике: цель, подсказка, лесенка ≥3 шагов, реплика из диалога, своя фраза."""

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_every_a1_twister_follows_method(self):
        from apps.curriculum.models import TongueTwister
        from apps.publishing.audit_weeks import audit_twister_method

        for tw in TongueTwister.objects.filter(week__level__code="A1").select_related("week__level"):
            r = AuditReport()
            audit_twister_method(r, f"Скороговорка {tw.number}", tw)
            self.assertEqual(r.errors, [], tw.number)
            self.assertGreaterEqual(len(tw.warmup), 3)

    def test_missing_method_is_an_error(self):
        from apps.curriculum.models import TongueTwister
        from apps.publishing.audit_weeks import audit_twister_method

        tw = TongueTwister.objects.get(number=8)
        tw.goal_ru, tw.warmup, tw.target_line = "", ["[A3]right[/]"], "This line is not in the dialogue."
        r = AuditReport()
        audit_twister_method(r, "Скороговорка 8", tw)
        text = " ".join(r.errors)
        self.assertIn("нет цели", text)
        self.assertIn("в разминке 1 шагов", text)
        self.assertIn("нет в диалоге", text)

    def test_week_page_shows_trainer_steps(self):
        response = self.client.get(reverse("curriculum:week", args=["a1", 8]))
        for step in ("Попробуйте звук отдельно", "Соберите по кусочкам", "Вернитесь к разговору", "Точность"):
            self.assertContains(response, step)
        self.assertContains(response, "Go straight and turn left.")


class A1PoemsTests(TestCase):
    """Семь стихов A1: маленькие истории с рифмой, строфами и разбором каждой строки."""

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_all_a1_poems_published_with_stanzas(self):
        from apps.poems.models import Poem

        poems = Poem.objects.filter(level__code="A1", is_published=True)
        self.assertEqual(poems.count(), 7)
        for poem in poems:
            lines = [ln for ln in poem.body.strip().splitlines() if ln.strip()]
            self.assertGreaterEqual(len(lines), 12, poem.number)
            self.assertIn("\n\n", poem.body, poem.number)
            self.assertEqual(len(poem.pronunciation), len(lines), poem.number)

    def test_poem_page_keeps_stanzas_and_gap_lines(self):
        response = self.client.get(reverse("stories:poem", args=[4]))
        self.assertContains(response, "stanza-start")
        self.assertContains(response, "One for You and One for Me")
        html = response.content.decode()
        self.assertEqual(html.count('class="fill-input gap-input"'), 5)

    def test_gap_numbers_count_only_text_lines(self):
        url = reverse("api:check_poem_gap", args=[3, 3])  # стих 3, пропуск «time» в строке 11
        ok = self.client.post(url, json.dumps({"answer": "time"}), content_type="application/json").json()
        self.assertTrue(ok["correct"])


class WeeklyVocabularyNormTests(TestCase):
    """Добор A1 до 500 единиц: недели, которые уже доведены до нормы 30–39."""

    FILLED_WEEKS = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14)

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_filled_weeks_meet_weekly_norm(self):
        from apps.curriculum.registry import WEEKLY_UNITS
        low, high = WEEKLY_UNITS["A1"]
        for n in self.FILLED_WEEKS:
            count = LexicalUnit.objects.filter(internal_level__code="A1", week__number=n).count()
            self.assertTrue(low <= count <= high, f"неделя {n}: {count}")

    def test_every_unit_of_filled_week_is_taught(self):
        for n in self.FILLED_WEEKS:
            scene = WeekScene.objects.get(week__level__code="A1", week__number=n)
            taught = set(Lesson.objects.filter(week=scene.week).values_list("units__uid", flat=True))
            taught |= set(scene.chunks.values_list("uid", flat=True))
            taught |= set(Story.objects.filter(week=scene.week).values_list("new_units__uid", flat=True))
            missing = LexicalUnit.objects.filter(week=scene.week).exclude(uid__in=taught)
            self.assertEqual(list(missing.values_list("lemma", flat=True)), [], f"неделя {n}")
