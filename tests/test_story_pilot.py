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
