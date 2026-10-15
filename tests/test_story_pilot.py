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
