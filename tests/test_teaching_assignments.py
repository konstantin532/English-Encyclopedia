"""Модели и поток назначений уроков группы."""
from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User
from apps.learning.models import IndependentAttempt
from apps.lessons.models import Lesson
from apps.teaching.models import AssignmentProgress, LessonAssignment, StudyGroup
from tests.runner import ensure_content


class AssignmentModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.teacher = User.objects.create_user(
            "teacher@example.com", "pass-12345", is_teacher=True,
        )
        cls.student = User.objects.create_user("student@example.com", "pass-12345")
        cls.group = StudyGroup.objects.create(teacher=cls.teacher, name="A1 group")
        cls.lesson = Lesson.objects.filter(is_published=True, level__code="A1").first()

    def create_assignment(self, *, due_date=None):
        return LessonAssignment.objects.create(
            teacher=self.teacher,
            group=self.group,
            lesson=self.lesson,
            due_date=due_date,
        )

    def create_attempt(self, *, assignment_progress=None):
        return IndependentAttempt.objects.create(
            user=self.student,
            lesson=self.lesson,
            skill="transfer",
            submitted="I have a small room.",
            outcome=IndependentAttempt.Outcome.SELF_REPORTED,
            assignment_progress=assignment_progress,
        )

    def test_reassigning_same_lesson_keeps_independent_assignment_progress(self):
        first = self.create_assignment(due_date=date(2026, 11, 5))
        second = self.create_assignment(due_date=date(2026, 11, 12))
        first_progress = AssignmentProgress.objects.create(
            assignment=first,
            student=self.student,
            status=AssignmentProgress.Status.IN_PROGRESS,
        )
        second_progress = AssignmentProgress.objects.create(
            assignment=second,
            student=self.student,
        )

        self.assertNotEqual(first.pk, second.pk)
        self.assertNotEqual(first_progress.pk, second_progress.pk)
        self.assertEqual(first_progress.status, AssignmentProgress.Status.IN_PROGRESS)
        self.assertEqual(second_progress.status, AssignmentProgress.Status.NOT_STARTED)
        self.assertEqual(first.due_date, date(2026, 11, 5))
        self.assertEqual(second.due_date, date(2026, 11, 12))

    def test_student_has_only_one_progress_record_per_assignment(self):
        assignment = self.create_assignment()
        AssignmentProgress.objects.create(assignment=assignment, student=self.student)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AssignmentProgress.objects.create(
                    assignment=assignment,
                    student=self.student,
                )

    def test_answer_links_to_exact_assignment_and_old_answers_remain_unlinked(self):
        assignment = self.create_assignment()
        progress = AssignmentProgress.objects.create(
            assignment=assignment,
            student=self.student,
        )

        historical = self.create_attempt()
        assigned = self.create_attempt(assignment_progress=progress)

        self.assertIsNone(historical.assignment_progress_id)
        self.assertEqual(assigned.assignment_progress, progress)
        self.assertEqual(progress.work.get(), assigned)
