"""Regression: scoring an exercise and scheduling its review form one unit of work."""
import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.drills.models import Exercise
from apps.learning.models import ExerciseAttempt, MistakeReview, UnitProgress
from tests.runner import ensure_content


class AtomicExerciseReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.exercise = Exercise.objects.get(lesson__slug="a1-verb-be", order=2)

    def setUp(self):
        self.user = User.objects.create_user(
            email="atomic-review@example.test", password="correct-horse-battery-2026"
        )
        self.client.force_login(self.user)

    def submit_wrong_answer(self):
        return self.client.post(
            reverse("api:check_exercise", args=[self.exercise.pk]),
            json.dumps({"answer": "definitely incorrect"}),
            content_type="application/json",
        )

    def test_scheduling_failure_rolls_back_attempt_and_progress(self):
        # Simulate a DB/service failure after record_attempt has written rows.
        # Before the fix, nested atomic(record_attempt) has already committed,
        # leaving an attempt and UnitProgress without the required review.
        with patch(
            "apps.api.views.schedule_review",
            side_effect=RuntimeError("injected review scheduling failure"),
        ) as scheduler:
            with self.assertRaisesRegex(
                RuntimeError, "injected review scheduling failure"
            ):
                self.submit_wrong_answer()
        scheduler.assert_called_once()
        self.assertFalse(ExerciseAttempt.objects.filter(user=self.user).exists())
        self.assertFalse(UnitProgress.objects.filter(user=self.user).exists())
        self.assertFalse(MistakeReview.objects.filter(user=self.user).exists())

    def test_successful_wrong_answer_commits_attempt_progress_and_queue(self):
        response = self.submit_wrong_answer()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["correct"])
        self.assertEqual(response.json()["retry_count"], 5)
        self.assertEqual(ExerciseAttempt.objects.filter(user=self.user).count(), 1)
        self.assertTrue(UnitProgress.objects.filter(user=self.user).exists())
        self.assertEqual(MistakeReview.objects.filter(user=self.user).count(), 1)
