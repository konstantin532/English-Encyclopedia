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
