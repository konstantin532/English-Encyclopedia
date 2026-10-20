"""Загрузка курса не стирает молча историю ответов учеников."""
import shutil
import tempfile
from io import StringIO
from pathlib import Path

import yaml
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings, tag

from apps.drills.models import Exercise
from apps.learning.models import ExerciseAttempt
from tests.runner import ensure_content

LESSON = "seed_lessons/a1_w01_l02_be.yaml"


@tag("slow")  # копирует и перезагружает весь курс
class ProgressSafetyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.user = get_user_model().objects.create_user("safe@example.com", password="pw-12345-x")
        cls.exercise = Exercise.objects.get(lesson__slug="a1-verb-be", order=5)
        ExerciseAttempt.objects.create(user=cls.user, exercise=cls.exercise, answer="x", is_correct=False)

    def load_without_exercise_5(self, *args):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            content = root / "content"
            shutil.copytree(settings.CONTENT_DIR, content)
            path = content / LESSON
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            data["exercises"] = [e for e in data["exercises"] if e["order"] != 5]
            path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            with override_settings(CONTENT_DIR=content, BASE_DIR=root):
                call_command("load_content", *args, stdout=StringIO())

    def test_removing_answered_exercise_is_refused(self):
        with self.assertRaisesMessage(CommandError, "ответы учеников"):
            self.load_without_exercise_5()
        self.assertTrue(ExerciseAttempt.objects.filter(exercise=self.exercise).exists())

    def test_explicit_flag_allows_removal(self):
        self.load_without_exercise_5("--allow-progress-loss")
        self.assertFalse(Exercise.objects.filter(pk=self.exercise.pk).exists())
