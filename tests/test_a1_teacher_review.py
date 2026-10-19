"""Teacher review uses explicit, protected human judgments, not auto-scoring."""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.learning.admin import IndependentAttemptReviewForm
from apps.learning.models import IndependentAttempt
from apps.lessons.models import Lesson
from tests.runner import ensure_content


class TeacherVerifiedIndependentResponseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.student = User.objects.create_user(
            email="independent-learner@example.test", password="ExamplePassword123!")
        self.staff = User.objects.create_superuser(
            email="independent-teacher@example.test", password="ExamplePassword123!")
        self.lesson = Lesson.objects.get(level__code="A1", order=20)
        self.attempt = IndependentAttempt.objects.create(
            user=self.student, lesson=self.lesson, skill="transfer",
            submitted="I like cooking.", outcome=IndependentAttempt.Outcome.SELF_REPORTED,
        )
        self.url = reverse(
            "admin:learning_independentattempt_change", args=[self.attempt.pk])

    def test_new_attempt_is_not_falsely_teacher_verified(self):
        self.assertEqual(
            self.attempt.teacher_verdict, IndependentAttempt.TeacherVerdict.UNREVIEWED)
        self.assertEqual(self.attempt.teacher_rubric, {})
        self.assertIsNone(self.attempt.reviewed_by)
        self.assertIsNone(self.attempt.reviewed_at)

    def test_student_cannot_open_teacher_review_screen(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_staff_can_record_specific_rubric_without_changing_answer(self):
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(self.url), "Передаёт смысл задания?")
        original = self.attempt.submitted
        result = self.client.post(self.url, {
            "teacher_verdict": "meets_task",
            "rubric_meaning": "yes",
            "rubric_form": "yes",
            "rubric_context": "yes",
            "teacher_note": "Фраза понятная, грамматика правильная, ситуация соблюдена.",
            "_save": "Сохранить",
        })
        self.assertEqual(result.status_code, 302)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.submitted, original)
        self.assertEqual(self.attempt.teacher_verdict, "meets_task")
        self.assertEqual(
            self.attempt.teacher_rubric,
            {"meaning": "yes", "form": "yes", "context": "yes"})
        self.assertEqual(self.attempt.reviewed_by, self.staff)
        self.assertIsNotNone(self.attempt.reviewed_at)

        self.client.force_login(self.student)
        page = self.client.get(
            reverse("learning:independent_check", args=[self.lesson.slug]))
        self.assertContains(page, "Проверено преподавателем:")
        self.assertContains(page, "Фраза понятная, грамматика правильная")

    def test_teacher_sees_the_original_variant_and_not_an_unrelated_answer(self):
        from apps.learning.understanding import understanding_bank
        self.attempt.task_variant = 2
        self.attempt.save(update_fields=["task_variant"])
        variant = understanding_bank()[self.lesson.slug]["transfer_variants"][1]
        self.client.force_login(self.staff)
        page = self.client.get(self.url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Исходная ситуация ученика")
        self.assertContains(page, variant["prompt"])
        self.assertContains(page, variant["model"])
        self.assertContains(page, "I like cooking.")

    def test_teacher_must_not_grade_a_task_whose_origin_has_disappeared(self):
        self.attempt.task_variant = 999
        self.attempt.save(update_fields=["task_variant"])
        self.client.force_login(self.staff)
        response = self.client.post(self.url, {
            "teacher_verdict": "meets_task",
            "rubric_meaning": "yes", "rubric_form": "yes",
            "rubric_context": "yes",
            "teacher_note": "This is a sufficient note, but provenance is missing.",
            "_save": "Сохранить",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Невозможно восстановить исходное задание")
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.teacher_verdict, "unreviewed")
        self.assertIsNone(self.attempt.reviewed_at)

    def test_invalid_or_inconsistent_staff_verdict_is_rejected(self):
        self.client.force_login(self.staff)
        partial = self.client.post(self.url, {
            "teacher_verdict": "meets_task",
            "rubric_meaning": "yes",
            "rubric_form": "partly",
            "rubric_context": "yes",
            "teacher_note": "Есть грамматическая неточность в текущей фразе.",
            "_save": "Сохранить",
        })
        self.assertEqual(partial.status_code, 200)
        self.assertContains(partial, "все три критерия")
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.teacher_verdict, "unreviewed")
        missing_note = self.client.post(self.url, {
            "teacher_verdict": "needs_work",
            "rubric_meaning": "partly",
            "rubric_form": "not_yet",
            "rubric_context": "yes",
            "teacher_note": "Нет",
            "_save": "Сохранить",
        })
        self.assertEqual(missing_note.status_code, 200)
        self.attempt.refresh_from_db()
        self.assertIsNone(self.attempt.reviewed_by)
