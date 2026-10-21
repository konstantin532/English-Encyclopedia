"""Reproductions from the independent audit of 343dd79 (2026-10-21)."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.management.commands.load_content import Command
from apps.drills.models import Exercise
from apps.learning.mistake_review import due_reviews
from apps.learning.models import IndependentAttempt, MistakeReview
from tests.runner import ensure_content


class FormTokenBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.user = get_user_model().objects.create_user("token-boundary@example.test")

    def test_invalid_unicode_tokens_are_rejected_without_writing_attempts(self):
        self.client.force_login(self.user)
        cases = (
            (reverse("learning:independent_check", args=["a1-verb-be"]),
             {"action": "batch"}, "batch_token"),
            (reverse("learning:transfer_pilot", args=["a1-verb-be"]),
             {"stage": "100"}, "token"),
            (reverse("learning:cafe_mission"),
             {"action": "send", "answer": "one tea"}, "token"),
        )
        for url, data, field in cases:
            self.assertEqual(self.client.get(url).status_code, 200)
            for token in ("я", "🔑", "valid-prefix-я", "", "a" * 100):
                with self.subTest(url=url, token=token):
                    response = self.client.post(url, {**data, field: token})
                    self.assertEqual(response.status_code, 400)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.user).exists())


class ArchivedDelayedReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.user = get_user_model().objects.create_user("archive-queue@example.test")

    def setUp(self):
        self.client.force_login(self.user)
        exercise = Exercise.objects.get(lesson__slug="a1-nouns-first-words", order=1)
        self.archived_review = MistakeReview.objects.create(
            user=self.user, exercise=exercise,
            due_at=timezone.now() - timedelta(days=2),
        )
        # Use the actual release loader: removing an exercise must preserve
        # its history, while withdrawing it from every learner-facing queue.
        loader = Command()
        loader.allow_progress_loss = False
        loader._load_exercises("audit", exercise.lesson, [])
        exercise.refresh_from_db()
        self.assertTrue(exercise.is_archived)
        self.live_exercise = Exercise.objects.get(lesson__slug="a1-verb-be", order=2)
        self.live_review = MistakeReview.objects.create(
            user=self.user, exercise=self.live_exercise,
            due_at=timezone.now() - timedelta(days=1),
        )

    def test_archive_cannot_block_the_next_available_question(self):
        self.assertEqual(list(due_reviews(self.user)), [self.live_review])
        response = self.client.get(reverse("learning:mistake_review"))
        self.assertEqual(response.context["task"]["id"], self.live_review.pk)
        self.assertEqual(self.client.get(reverse("learning:dashboard")).context[
            "mistake_review_due_count"], 1)

    def test_future_archive_and_unpublished_lesson_do_not_advertise_a_review(self):
        future = timezone.now() + timedelta(days=2)
        MistakeReview.objects.filter(pk=self.archived_review.pk).update(due_at=future)
        self.live_exercise.lesson.is_published = False
        self.live_exercise.lesson.save(update_fields=["is_published"])
        page = self.client.get(reverse("learning:mistake_review"))
        self.assertIsNone(page.context["next_due"])
        dashboard = self.client.get(reverse("learning:dashboard"))
        self.assertEqual(dashboard.context["mistake_review_due_count"], 0)
        self.assertIsNone(dashboard.context["mistake_review_waiting"])

    def test_post_to_archive_is_rejected_and_preserved_history_is_unchanged(self):
        response = self.client.post(reverse("learning:mistake_review"), {
            "review_id": self.archived_review.pk, "index": 0, "choice": 0,
        })
        self.assertEqual(response.status_code, 404)
        self.archived_review.refresh_from_db()
        self.assertEqual(self.archived_review.current_index, 0)
        self.assertIsNone(self.archived_review.completed_at)

    def test_unpublished_future_lesson_is_not_advertised(self):
        MistakeReview.objects.filter(pk=self.live_review.pk).update(
            due_at=timezone.now() + timedelta(days=2),
        )
        self.live_exercise.lesson.is_published = False
        self.live_exercise.lesson.save(update_fields=["is_published"])
        self.assertIsNone(self.client.get(reverse("learning:mistake_review")).context["next_due"])
        self.assertIsNone(self.client.get(reverse("learning:dashboard")).context["mistake_review_waiting"])
