"""Negative/positive tests for opt-in first-two-week transfer retention.

These are engineering contract tests, not empirical evidence of learning gains.
"""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.learning.models import IndependentAttempt, UnitProgress
from apps.lessons.models import Lesson
from tests.runner import ensure_content


class A1TransferRetentionPilotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.user = User.objects.create_user(
            email="pilot-learner@example.test", password="ExamplePassword123!"
        )
        self.other = User.objects.create_user(
            email="other-pilot@example.test", password="ExamplePassword123!"
        )
        self.client.force_login(self.user)
        self.lesson = Lesson.objects.get(slug="a1-verb-be")
        self.url = reverse("learning:transfer_pilot", args=[self.lesson.slug])

    def _post(self, client=None, answer="Hi, I'm Alex. I'm from Boston."):
        client = client or self.client
        page = client.get(self.url)
        assert page.status_code == 200
        ctx = page.context
        return client.post(self.url, {
            "token": ctx["token"],
            "stage": ctx["stage"][1],
            "answer": answer,
            "assistance": "no_help",
        })

    def _first(self):
        result = self._post()
        self.assertEqual(result.status_code, 302)
        return IndependentAttempt.objects.get(user=self.user, task_variant=100)

    def test_only_selected_lessons_are_supported(self):
        for slug in ("a1-verb-be", "a1-have-like-can-do", "a1-cafe-order"):
            self.assertEqual(self.client.get(
                reverse("learning:transfer_pilot", args=[slug])).status_code, 200)
        self.assertEqual(self.client.get(reverse(
            "learning:transfer_pilot", args=["a1-nouns-first-words"])).status_code, 400)

    def test_login_is_required_and_other_user_cannot_view_my_answers(self):
        outsider = Client()
        self.assertEqual(outsider.get(self.url).status_code, 302)
        self._first()
        outsider.force_login(self.other)
        result = outsider.get(self.url)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(list(result.context["attempts"]), [])
        self.assertNotContains(result, "Hi, I'm Alex.")

    def test_prompt_shown_before_submission_never_leaks_teacher_sample(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "Hello! I'm Alex. I'm from Boston.")
        self.assertNotContains(response, "Sam. I'm your neighbor.")
        self.assertContains(response, 'name="answer"')
        self.assertNotContains(response, 'name="model"')

    def test_first_attempt_stays_unverified_and_does_not_change_unit_progress(self):
        attempt = self._first()
        self.assertEqual(attempt.outcome, IndependentAttempt.Outcome.SELF_REPORTED)
        self.assertEqual(attempt.teacher_verdict,
                         IndependentAttempt.TeacherVerdict.UNREVIEWED)
        self.assertEqual(attempt.assistance, "no_help")
        self.assertEqual(attempt.prompt_snapshot != "", True)
        self.assertTrue(attempt.model_snapshot)
        self.assertEqual(UnitProgress.objects.filter(user=self.user).count(), 0)
        self.assertContains(self.client.get(self.url), "Следующий этап пока закрыт")

    def test_seven_and_thirty_days_require_real_elapsed_time_and_new_prompts(self):
        first = self._first()
        self.assertEqual(self.client.get(self.url).context["ready"], False)
        self.assertEqual(self.client.post(self.url, {
            "stage": "101", "answer": "Hi there", "assistance": "no_help",
            "token": "forged",
        }).status_code, 400)
        IndependentAttempt.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(days=8))
        page = self.client.get(self.url)
        self.assertEqual(page.context["stage"][1], 101)
        self.assertNotEqual(page.context["mission"]["prompt"], first.prompt_snapshot)
        second = self._post(answer="Hi, my name is Sam. I'm your neighbor.")
        self.assertEqual(second.status_code, 302)
        self.assertEqual(self.client.get(self.url).context["ready"], False)

        IndependentAttempt.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(days=31))
        page30 = self.client.get(self.url)
        self.assertEqual(page30.context["stage"][1], 102)
        third = self._post(answer="Hello, I'm Kim. What's your name?")
        self.assertEqual(third.status_code, 302)
        self.assertTrue(self.client.get(self.url).context["completed"])
        self.assertEqual(set(IndependentAttempt.objects.filter(
            user=self.user).values_list("task_variant", flat=True)), {100, 101, 102})

    def test_missing_day_seven_does_not_block_day_thirty_or_fabricate_attendance(self):
        first = self._first()
        IndependentAttempt.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(days=31))
        result = self.client.get(self.url)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.context["stage"][1], 102)
        self.assertEqual(result.context["ready"], True)
        saved = self._post(answer="Hello, I'm Kim. What's your name?")
        self.assertEqual(saved.status_code, 302)
        self.assertTrue(self.client.get(self.url).context["completed"])
        self.assertFalse(IndependentAttempt.objects.filter(
            user=self.user, lesson=self.lesson, task_variant=101).exists())
        self.assertEqual(set(IndependentAttempt.objects.filter(
            user=self.user).values_list("task_variant", flat=True)), {100, 102})

    def test_stale_token_and_double_submit_do_not_create_extra_evidence(self):
        page = self.client.get(self.url)
        payload = {
            "token": page.context["token"], "stage": "100",
            "answer": "I'm Jane.", "assistance": "no_help",
        }
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.assertEqual(self.client.post(self.url, payload).status_code, 400)
        self.assertEqual(IndependentAttempt.objects.filter(
            user=self.user, lesson=self.lesson, task_variant=100).count(), 1)

    def test_cross_device_duplicate_stage_blocked_by_database(self):
        self._first()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                IndependentAttempt.objects.create(
                    user=self.user, lesson=self.lesson, skill="transfer",
                    task_variant=100, batch_token="pilot-anotherdevice",
                    submitted="Another answer", outcome="self_reported",
                )

    def test_bad_input_does_not_change_records(self):
        page = self.client.get(self.url)
        token = page.context["token"]
        for answer, assistance in (("", "no_help"), ("A" * 401, "no_help"),
                                   ("Hello", "invented")):
            with self.subTest(answer=answer[:10], assistance=assistance):
                res = self.client.post(self.url, {
                    "token": token, "stage": "100",
                    "answer": answer, "assistance": assistance,
                })
                self.assertEqual(res.status_code, 400)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.user).exists())

    def test_experimental_evidence_does_not_displace_regular_independent_checks(self):
        self._first()
        normal = self.client.get(reverse(
            "learning:independent_check", args=[self.lesson.slug]))
        self.assertEqual(normal.status_code, 200)
        self.assertContains(normal, "Сначала все четыре ответа")
        self.assertEqual(UnitProgress.objects.filter(user=self.user).count(), 0)

    def test_html_from_user_is_escaped(self):
        result = self._post(answer="<script>alert(9)</script>")
        self.assertEqual(result.status_code, 302)
        page = self.client.get(self.url)
        self.assertNotContains(page, "<script>alert(9)</script>", html=False)
        self.assertContains(page, "Следующий этап пока закрыт")
