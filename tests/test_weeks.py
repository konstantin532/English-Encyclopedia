from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.curriculum.models import TongueTwister, Week, WeekScene
from apps.learning.models import WeekGoal


class WeekModelTests(TestCase):
    def test_scene_twister_goal(self):
        week = Week.objects.get(level__code="A1", number=1)
        scene = WeekScene.objects.create(week=week, can_do_ru="Я смогу…", mission_ru="…", script=[])
        TongueTwister.objects.create(number=1, week=week, series="sounds", text="[T2]This[/]", source="original")
        user = User.objects.create_user("u@example.com", "s3cret-pass-123")
        WeekGoal.objects.create(user=user, week=week, status="done")
        week.refresh_from_db()
        self.assertEqual(week.scene, scene)
        self.assertEqual(week.twister.number, 1)
        self.assertEqual(week.global_number, 1)
        self.assertEqual(Week.objects.get(level__code="A1+", number=1).global_number, 15)
        with self.assertRaises(IntegrityError):
            WeekGoal.objects.create(user=user, week=week, status="not_yet")


import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import override_settings

from apps.stories.script import build_lines

SAMPLE_WEEK = """level: A1
week: 1
can_do_ru: "Я смогу представиться."
mission_ru: "Скажите своё имя вслух три раза."
ambience: morning_home
chunks: []
script:
  - speaker: tom
    text: "[S7]Good morning[/]! [T8]I[/] [D1]am[/] [S1]Tom[/]."
    emotion: happy
    ru: "Доброе утро! Я Том."
  - speaker: anna
    text: "[T8]I[/] [D1]am[/] [S1]Anna[/]."
  - speaker: tom
    text: "[D1]Is[/] [T2]this[/] [T3]your[/] [S2]house[/]?"
  - speaker: anna
    text: "[O4]Yes[/]. [T8]It[/] [D1]is[/] [J2]new[/]."
  - speaker: tom
    text: "[T8]It[/] [D1]is[/] [J3]nice[/]!"
    emotion: excited
  - speaker: anna
    text: "[O2]Thank you[/], [S1]Tom[/]."
twister:
  number: 1
  series: sounds
  text: "[T2]This[/] [D1]is[/] [T2]this[/]."
  ipa: "/ðɪs ɪz ðɪs/"
  focus_sounds: [dh]
  source: original
"""


class WeekLoaderTests(TestCase):
    @contextmanager
    def content_with_week(self, text):
        tmp = Path(tempfile.mkdtemp())
        try:
            root = tmp / "content"
            shutil.copytree(settings.CONTENT_DIR, root)
            (root / "seed_weeks").mkdir(exist_ok=True)
            (root / "seed_weeks" / "a1_w01.yaml").write_text(text, encoding="utf-8")
            with override_settings(CONTENT_DIR=root):
                yield root
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_plan_fills_weeks(self):
        call_command("load_content", verbosity=0)
        w = Week.objects.get(level__code="A1", number=8)
        self.assertEqual((w.sphere, w.grammar_markers), ("city", ["P1", "A6"]))
        self.assertEqual(w.situation_ru, "Как пройти?")

    def test_week_file_loads_idempotently(self):
        with self.content_with_week(SAMPLE_WEEK):
            call_command("load_content", verbosity=0)
            call_command("load_content", verbosity=0)
        scene = WeekScene.objects.get(week__level__code="A1", week__number=1)
        self.assertEqual(len(scene.script), 6)
        self.assertEqual(scene.can_do_ru, "Я смогу представиться.")
        self.assertEqual(TongueTwister.objects.get(number=1).week, scene.week)
        self.assertEqual(WeekScene.objects.count(), 1)
        self.assertEqual(scene.audio, {})

    def test_unknown_speaker_rejected(self):
        with self.content_with_week(SAMPLE_WEEK.replace("speaker: tom", "speaker: nobody", 1)):
            with self.assertRaisesMessage(CommandError, "nobody"):
                call_command("load_content", verbosity=0)

    def test_unknown_chunk_rejected(self):
        with self.content_with_week(SAMPLE_WEEK.replace("chunks: []", "chunks: [LX-99999]")):
            with self.assertRaisesMessage(CommandError, "LX-99999"):
                call_command("load_content", verbosity=0)

    def test_build_lines_emotion_label(self):
        lines, speakers = build_lines([{"speaker": "tom", "text": "Hi", "emotion": "surprised"},
                                       {"speaker": "anna", "text": "Hi", "ru": "Привет"}])
        self.assertEqual((lines[0]["name"], lines[0]["emotion_ru"], lines[1]["emotion_ru"]), ("Том", "удивлённо", ""))
        self.assertEqual((lines[1]["ru"], lines[1]["kind"], lines[1]["emotion"]), ("Привет", "speech", "neutral"))
        self.assertEqual([s["id"] for s in speakers], ["tom", "anna"])
