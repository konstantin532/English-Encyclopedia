"""A1 verified mistakes receive five novel, delayed, private practice questions."""
import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.drills.models import Exercise
from apps.drills.retry_guidance import PILOT_SLUGS
from apps.learning.mistake_review import COUNT, question_bank, variants_for
from apps.learning.models import ExerciseAttempt, MistakeReview, UnitProgress
from tests.runner import ensure_content


class A1MistakeReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.choice = Exercise.objects.get(lesson__slug="a1-verb-be", order=2)
        cls.transfer = Exercise.objects.get(lesson__slug="a1-nouns-first-words", order=4)

    def setUp(self):
        self.user = User.objects.create_user(email="reviewer@example.test", password="TestPassword123!")
        self.client.force_login(self.user)

    def answer_original(self, exercise, value):
        return self.client.post(
            reverse("api:check_exercise", args=[exercise.pk]),
            json.dumps({"answer": value}), content_type="application/json",
        ).json()

    def test_every_mistake_has_five_distinct_new_prompts(self):
        catalog = question_bank()
        self.assertEqual(set(catalog), PILOT_SLUGS)
        self.assertEqual(sum(len(variants) for row in catalog.values() for variants in row.values()), 215)
        for slug, row in catalog.items():
            for number, variants in row.items():
                with self.subTest(slug=slug, number=number):
                    exercise = Exercise.objects.get(lesson__slug=slug, order=int(number))
                    self.assertEqual(len(variants), COUNT)
                    self.assertEqual(len({q[0] for q in variants}), COUNT)
                    self.assertTrue(all(len(q[2]) == 3 and q[3] in range(3) for q in variants))
                    self.assertTrue(all(q[0] != exercise.prompt_ru for q in variants))
                    self.assertEqual(variants_for(exercise), variants)

    def test_error_waits_two_days_and_does_not_return_immediately(self):
        before = timezone.now()
        response = self.answer_original(self.choice, "is")
        self.assertFalse(response["correct"])
        self.assertEqual(response["retry_count"], COUNT)
        item = MistakeReview.objects.get(user=self.user, exercise=self.choice)
        self.assertGreaterEqual(item.due_at, before + timedelta(days=2))
        self.assertLessEqual(item.due_at, timezone.now() + timedelta(days=2, minutes=1))
        self.assertEqual(item.current_index, 0)
        self.assertEqual(ExerciseAttempt.objects.filter(user=self.user, exercise=self.choice, is_correct=False).count(), 1)
        for progress in UnitProgress.objects.filter(user=self.user, unit__in=self.choice.units.all()):
            self.assertGreater(progress.next_review_at, timezone.now() + timedelta(days=1, hours=23))
        self.assertNotContains(self.client.get(reverse("learning:mistake_review")), "Новый вопрос 1 из 5")
        regular = self.client.get(reverse("learning:review"))
        self.assertNotContains(regular, self.choice.prompt_ru)

    def test_repeat_mistake_before_due_keeps_first_due_date(self):
        self.answer_original(self.choice, "is")
        original_due = MistakeReview.objects.get(user=self.user, exercise=self.choice).due_at
        self.answer_original(self.choice, "am")
        item = MistakeReview.objects.get(user=self.user, exercise=self.choice)
        self.assertEqual(item.due_at, original_due)
        self.assertEqual(MistakeReview.objects.filter(user=self.user, exercise=self.choice).count(), 1)

    def test_open_transfer_mismatch_is_not_assumed_wrong_or_scheduled(self):
        before = ExerciseAttempt.objects.filter(user=self.user).count()
        data = self.answer_original(self.transfer, "This book belongs to me.")
        self.assertEqual(data["assessment"], "needs_review")
        self.assertNotIn("retry_scheduled_at", data)
        self.assertEqual(ExerciseAttempt.objects.filter(user=self.user).count(), before)
        self.assertFalse(MistakeReview.objects.filter(user=self.user).exists())

    def test_all_five_correct_finish_only_after_48_hours(self):
        self.answer_original(self.choice, "is")
        item = MistakeReview.objects.get(user=self.user, exercise=self.choice)
        item.due_at = timezone.now() - timedelta(seconds=1)
        item.save(update_fields=["due_at"])
        url = reverse("learning:mistake_review")
        for index, question in enumerate(variants_for(self.choice)):
            page = self.client.get(url)
            self.assertContains(page, f"Новый вопрос {index + 1} из 5")
            self.assertNotContains(page, 'name="answer"')
            self.assertNotContains(page, 'name="correct"')
            for option in question[2]:
                self.assertContains(page, option)
            response = self.client.post(url, {
                "review_id": item.pk, "index": index, "choice": question[3],
            })
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Верно!")
            if index != 4:
                self.assertContains(response, "Следующий новый вопрос")
                self.assertNotContains(response, f"Новый вопрос {index + 2} из 5")
        item.refresh_from_db()
        self.assertIsNotNone(item.completed_at)
        self.assertEqual(item.current_index, 5)
        self.assertEqual(item.correct_count, 5)
        self.assertFalse(MistakeReview.objects.filter(user=self.user, completed_at__isnull=True).exists())

    def test_one_wrong_requeues_next_cycle_after_two_days_not_now(self):
        self.answer_original(self.choice, "am")
        item = MistakeReview.objects.get(user=self.user, exercise=self.choice)
        item.due_at = timezone.now() - timedelta(seconds=1)
        item.save(update_fields=["due_at"])
        url = reverse("learning:mistake_review")
        for index, question in enumerate(variants_for(self.choice)):
            selected = (question[3] + 1) % 3 if index == 0 else question[3]
            response = self.client.post(url, {
                "review_id": item.pk, "index": index, "choice": selected,
            })
            self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertIsNone(item.completed_at)
        self.assertEqual(item.current_index, 0)
        self.assertEqual(item.correct_count, 0)
        self.assertGreater(item.due_at, timezone.now() + timedelta(days=1))
        self.assertNotContains(self.client.get(url), "Новый вопрос 1 из 5")

    def test_wrong_user_cannot_answer_or_view_others_session(self):
        self.answer_original(self.choice, "is")
        item = MistakeReview.objects.get(user=self.user, exercise=self.choice)
        item.due_at = timezone.now() - timedelta(seconds=1)
        item.save(update_fields=["due_at"])
        stranger = User.objects.create_user(email="another@example.test", password="TestPassword123!")
        self.client.force_login(stranger)
        url = reverse("learning:mistake_review")
        self.assertNotContains(self.client.get(url), "Новый вопрос 1 из 5")
        response = self.client.post(url, {"review_id": item.pk, "index": 0, "choice": 0})
        self.assertEqual(response.status_code, 404)
        item.refresh_from_db()
        self.assertEqual(item.current_index, 0)

    def test_stale_duplicate_and_early_requests_are_rejected(self):
        self.answer_original(self.choice, "is")
        item = MistakeReview.objects.get(user=self.user, exercise=self.choice)
        url = reverse("learning:mistake_review")
        premature = self.client.post(url, {"review_id": item.pk, "index": 0, "choice": 1})
        self.assertEqual(premature.status_code, 400)
        item.due_at = timezone.now() - timedelta(seconds=1)
        item.save(update_fields=["due_at"])
        response = self.client.post(url, {"review_id": item.pk, "index": 0, "choice": 1})
        self.assertEqual(response.status_code, 200)
        duplicate = self.client.post(url, {"review_id": item.pk, "index": 0, "choice": 1})
        self.assertEqual(duplicate.status_code, 400)
        item.refresh_from_db()
        self.assertEqual(item.current_index, 1)

    def test_logged_out_users_do_not_get_delayed_queue(self):
        self.client.logout()
        response = self.client.get(reverse("learning:mistake_review"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        guest_data = self.answer_original(self.choice, "am")
        self.assertNotIn("retry_scheduled_at", guest_data)
        self.assertEqual(MistakeReview.objects.count(), 0)

    def test_open_transfer_can_opt_in_without_a_negative_score(self):
        ex = self.transfer
        response = self.answer_original(ex, "This is my new phone.")
        self.assertEqual(response["assessment"], "needs_review")
        self.assertTrue(response["self_review_available"])
        self.assertFalse(ExerciseAttempt.objects.filter(user=self.user, exercise=ex).exists())
        before = timezone.now()
        requested = self.client.post(reverse("learning:request_optional_review", args=[ex.pk]))
        self.assertEqual(requested.status_code, 200)
        self.assertTrue(requested.json()["scheduled"])
        item = MistakeReview.objects.get(user=self.user, exercise=ex)
        self.assertGreaterEqual(item.due_at, before + timedelta(days=2))
        self.assertEqual(UnitProgress.objects.filter(user=self.user).count(), 0)
        self.assertNotContains(self.client.get(reverse("learning:mistake_review")), "Новый вопрос 1 из 5")
        again = self.client.post(reverse("learning:request_optional_review", args=[ex.pk]))
        self.assertEqual(again.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(MistakeReview.objects.filter(user=self.user, exercise=ex).count(), 1)

    def test_all_twelve_open_transfer_question_packs_are_reachable_by_opt_in(self):
        transfers = Exercise.objects.filter(
            lesson__slug__in=PILOT_SLUGS,
            kind=Exercise.Kind.FILL, stage=Exercise.Stage.TRANSFER,
        ).select_related("lesson")
        self.assertEqual(transfers.count(), 12)
        for ex in transfers:
            with self.subTest(slug=ex.lesson.slug, number=ex.order):
                response = self.client.post(reverse("learning:request_optional_review", args=[ex.pk]))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(variants_for(ex)), 5)
        self.assertEqual(MistakeReview.objects.filter(user=self.user).count(), 12)

    def test_voluntary_endpoint_does_not_schedule_unrelated_objective_or_guest(self):
        url = reverse("learning:request_optional_review", args=[self.choice.pk])
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertFalse(MistakeReview.objects.exists())
        self.client.logout()
        self.assertEqual(
            self.client.post(reverse("learning:request_optional_review", args=[self.transfer.pk])).status_code,
            302,
        )
        self.assertFalse(MistakeReview.objects.exists())


    def test_new_family_lessons_schedule_and_open_five_fresh_questions(self):
        for slug, number, wrong in (
            ("a1-family-photo", 1, "Who this?"),
            ("a1-family-possession", 1, "his brother"),
        ):
            with self.subTest(lesson=slug):
                exercise = Exercise.objects.get(lesson__slug=slug, order=number)
                data = self.answer_original(exercise, wrong)
                self.assertFalse(data["correct"])
                self.assertEqual(data["retry_count"], 5)
                self.assertNotIn("answer", data)
                self.assertTrue(data["feedback_ru"])
                item = MistakeReview.objects.get(user=self.user, exercise=exercise)
                self.assertGreater(item.due_at, timezone.now() + timedelta(days=1))
                self.assertEqual(len(variants_for(exercise)), 5)
                self.assertEqual(item.current_index, 0)
                item.due_at = timezone.now() - timedelta(seconds=1)
                item.save(update_fields=["due_at"])
                # The due page contains the new question, not the original.
                response = self.client.get(reverse("learning:mistake_review"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Новый вопрос 1 из 5")
                # Retire this review to check the second lesson independently.
                item.completed_at = timezone.now()
                item.save(update_fields=["completed_at"])
