"""Regression checks: every required act in an A1 transfer prompt must be present.

This is a narrow, source-backed content contract, not proof that learners
can produce the response without cues or that they have attained CEFR A1.
"""
import json
from pathlib import Path

import yaml
from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.drills.models import Exercise
from tests.runner import ensure_content


LESSON_FILE = (Path(settings.BASE_DIR) / "content" / "seed_lessons"
               / "a1_w14_l28_review.yaml")
EXERCISE_UID = "EX-00161"


class FinalTransferContractTests(SimpleTestCase):
    def test_incomplete_intro_cannot_satisfy_two_part_task(self):
        lesson = yaml.safe_load(LESSON_FILE.read_text(encoding="utf-8"))
        task = next(item for item in lesson["exercises"]
                    if item["uid"] == EXERCISE_UID)
        self.assertEqual(task["stage"], "transfer")
        self.assertIn("откуда", task["prompt_ru"])
        self.assertIn("говорите по-английски", task["prompt_ru"])

        exercise = Exercise(answer=task["answer"], accepted=task["accepted"])
        for incomplete in ("I am from Russia.", "I'm from Russia."):
            with self.subTest(incomplete=incomplete):
                self.assertFalse(exercise.is_correct(incomplete))
        for complete in (
            "I am from Russia. I can speak English.",
            "I'm from Russia. I speak English.",
            "I am from Russia. I speak English.",
        ):
            with self.subTest(complete=complete):
                self.assertTrue(exercise.is_correct(complete))


class FinalTransferApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.exercise = Exercise.objects.get(uid=EXERCISE_UID)

    def submit(self, text):
        response = self.client.post(
            reverse("api:check_exercise", args=[self.exercise.pk]),
            data=json.dumps({"answer": text}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_unfinished_task_is_not_granted_a_model_match(self):
        for incomplete in ("I am from Russia.", "I'm from Russia."):
            with self.subTest(incomplete=incomplete):
                result = self.submit(incomplete)
                self.assertFalse(result["correct"])
                self.assertEqual(result.get("assessment"), "needs_review")
                self.assertFalse(result["saved"])

    def test_complete_task_still_matches(self):
        result = self.submit("I'm from Russia. I can speak English.")
        self.assertTrue(result["correct"])
        self.assertEqual(result.get("assessment"), "model_match")
