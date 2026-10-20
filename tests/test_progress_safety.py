"""Загрузка курса не стирает молча историю ответов учеников."""
import shutil
import tempfile
from io import StringIO
from pathlib import Path

import yaml
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
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

    def test_removed_exercise_with_history_is_archived_not_deleted(self):
        self.load_without_exercise_5()
        archived = Exercise.all_objects.get(pk=self.exercise.pk)
        self.assertTrue(archived.is_archived)
        self.assertFalse(Exercise.objects.filter(pk=self.exercise.pk).exists())  # скрыто от учеников
        self.assertTrue(ExerciseAttempt.objects.filter(exercise=archived).exists())  # история цела

    def test_explicit_flag_deletes_with_history(self):
        self.load_without_exercise_5("--allow-progress-loss")
        self.assertFalse(Exercise.all_objects.filter(pk=self.exercise.pk).exists())
        self.assertFalse(ExerciseAttempt.objects.filter(user=self.user).exists())

    def test_reordering_keeps_history_on_the_same_exercise(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            content = root / "content"
            shutil.copytree(settings.CONTENT_DIR, content)
            path = content / LESSON
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            for item in data["exercises"]:
                item["order"] = {5: 1, 1: 5}.get(item["order"], item["order"])
            path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            with override_settings(CONTENT_DIR=content, BASE_DIR=root):
                call_command("load_content", stdout=StringIO())
        moved = Exercise.objects.get(pk=self.exercise.pk)
        self.assertEqual(moved.order, 1)
        self.assertEqual(moved.uid, self.exercise.uid)
        self.assertTrue(ExerciseAttempt.objects.filter(exercise=moved).exists())

    def test_every_course_exercise_has_a_permanent_uid(self):
        self.assertFalse(Exercise.objects.filter(lesson__level__code="A1", uid__isnull=True).exists())


class FieldLengthTests(TestCase):
    """SQLite не проверяет длину строк, PostgreSQL (продакшен) — проверяет. Ловим заранее."""

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_loaded_content_fits_varchar_columns(self):
        from django.apps import apps
        from django.db import models

        too_long = []
        for model in apps.get_models():
            if model._meta.app_label not in {"lexicon", "lessons", "drills", "stories", "poems", "curriculum", "taxonomy"}:
                continue
            fields = [f for f in model._meta.concrete_fields if isinstance(f, models.CharField) and f.max_length]
            for row in model.objects.values("pk", *[f.name for f in fields]):
                for f in fields:
                    value = row[f.name] or ""
                    if len(value) > f.max_length:
                        too_long.append(f"{model.__name__}.{f.name} #{row['pk']}: {len(value)} > {f.max_length}")
        self.assertEqual(too_long, [])
