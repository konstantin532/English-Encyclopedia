"""Модели и поток назначений уроков группы."""
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.learning.models import IndependentAttempt
from apps.lessons.models import Lesson
from apps.teaching.assignments import (
    assignment_is_overdue,
    complete_assignment,
    create_lesson_assignment,
    start_assignment,
    withdraw_assignments_for_group,
)
from apps.teaching.models import AssignmentProgress, GroupMembership, LessonAssignment, StudyGroup
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


class AssignmentRulesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        make_user = User.objects.create_user
        cls.teacher = make_user("teacher-rules@example.com", "pass-12345", is_teacher=True)
        cls.other_teacher = make_user("teacher-other@example.com", "pass-12345", is_teacher=True)
        cls.student = make_user("student-rules@example.com", "pass-12345")
        cls.late_student = make_user("late-student@example.com", "pass-12345")
        cls.group = StudyGroup.objects.create(teacher=cls.teacher, name="Assignment group")
        cls.other_group = StudyGroup.objects.create(teacher=cls.other_teacher, name="Other group")
        GroupMembership.objects.create(group=cls.group, student=cls.student)
        cls.lesson = Lesson.objects.filter(is_published=True, level__code="A1").first()

    def assign(self, *, due_date=None):
        return create_lesson_assignment(
            teacher=self.teacher,
            group=self.group,
            lesson=self.lesson,
            due_date=due_date,
        )

    def test_late_joiner_does_not_receive_an_existing_assignment(self):
        assignment = self.assign()
        GroupMembership.objects.create(group=self.group, student=self.late_student)

        self.assertTrue(
            AssignmentProgress.objects.filter(
                assignment=assignment,
                student=self.student,
            ).exists()
        )
        self.assertFalse(
            AssignmentProgress.objects.filter(
                assignment=assignment,
                student=self.late_student,
            ).exists()
        )

    def test_reassigning_same_lesson_creates_a_new_instance(self):
        first = self.assign(due_date=date(2026, 11, 5))
        first_progress = first.progress_records.get(student=self.student)
        first_progress = start_assignment(self.student, first_progress)
        second = self.assign(due_date=date(2026, 11, 12))
        second_progress = second.progress_records.get(student=self.student)

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(first_progress.status, AssignmentProgress.Status.IN_PROGRESS)
        self.assertEqual(second_progress.status, AssignmentProgress.Status.NOT_STARTED)
        self.assertEqual(first.due_date, date(2026, 11, 5))
        self.assertEqual(second.due_date, date(2026, 11, 12))

    def test_due_date_is_not_overdue_until_the_local_day_ends(self):
        due_date = date(2026, 11, 5)
        assignment = self.assign(due_date=due_date)
        progress = assignment.progress_records.get(student=self.student)
        moscow = ZoneInfo("Europe/Moscow")
        last_second = datetime(2026, 11, 5, 23, 59, 59, tzinfo=moscow)
        next_midnight = datetime(2026, 11, 6, 0, 0, tzinfo=moscow)

        self.assertFalse(assignment_is_overdue(progress, now=last_second))
        self.assertTrue(assignment_is_overdue(progress, now=next_midnight))

    def test_assignment_without_due_date_never_becomes_overdue(self):
        assignment = self.assign()
        progress = assignment.progress_records.get(student=self.student)

        self.assertFalse(
            assignment_is_overdue(
                progress,
                now=datetime(2027, 1, 1, 0, 0, tzinfo=ZoneInfo("Europe/Moscow")),
            )
        )

    def test_previous_completion_is_explicit_and_not_inferred_from_old_attempts(self):
        IndependentAttempt.objects.create(
            user=self.student,
            lesson=self.lesson,
            skill="transfer",
            submitted="I have a small room.",
            outcome=IndependentAttempt.Outcome.SELF_REPORTED,
        )
        assignment = self.assign(due_date=date(2026, 10, 30))
        progress = assignment.progress_records.get(student=self.student)
        now = datetime(2026, 10, 31, 12, 0, tzinfo=ZoneInfo("Europe/Moscow"))

        self.assertEqual(progress.status, AssignmentProgress.Status.NOT_STARTED)
        self.assertTrue(assignment_is_overdue(progress, now=now))

        complete_assignment(
            self.student,
            progress,
            previously_completed=True,
            now=now,
        )

        progress.refresh_from_db()
        self.assertEqual(progress.status, AssignmentProgress.Status.COMPLETED)
        self.assertEqual(
            progress.completion_source,
            AssignmentProgress.CompletionSource.PREVIOUSLY_COMPLETED,
        )
        self.assertFalse(assignment_is_overdue(progress, now=now))

    def test_completed_or_withdrawn_assignment_is_not_overdue(self):
        assignment = self.assign(due_date=date(2026, 10, 30))
        progress = assignment.progress_records.get(student=self.student)
        now = datetime(2026, 10, 31, 12, 0, tzinfo=ZoneInfo("Europe/Moscow"))

        progress = complete_assignment(self.student, progress, now=now)
        self.assertFalse(assignment_is_overdue(progress, now=now))

        other_assignment = self.assign(due_date=date(2026, 10, 30))
        withdrawn = other_assignment.progress_records.get(student=self.student)
        withdraw_assignments_for_group(self.student, self.group, now=now)
        withdrawn.refresh_from_db()
        self.assertEqual(withdrawn.status, AssignmentProgress.Status.WITHDRAWN)
        self.assertFalse(assignment_is_overdue(withdrawn, now=now))

    def test_teacher_can_assign_only_own_groups_and_published_lessons(self):
        with self.assertRaises(PermissionDenied):
            create_lesson_assignment(
                teacher=self.other_teacher,
                group=self.group,
                lesson=self.lesson,
            )

        self.lesson.is_published = False
        self.lesson.save(update_fields=["is_published"])
        with self.assertRaises(ValidationError):
            self.assign()

    def test_leaving_withdraws_open_work_but_preserves_completion_and_answers(self):
        assignment = self.assign()
        completed = complete_assignment(
            self.student, assignment.progress_records.get(student=self.student),
        )
        open_progress = self.assign().progress_records.get(student=self.student)
        attempt = IndependentAttempt.objects.create(
            user=self.student, lesson=self.lesson, skill="transfer",
            submitted="This is my room.", outcome="self_reported",
            assignment_progress=open_progress,
        )
        self.client.force_login(self.student)
        self.client.post(reverse("teaching:leave"))
        completed.refresh_from_db()
        open_progress.refresh_from_db()
        self.assertEqual(completed.status, AssignmentProgress.Status.COMPLETED)
        self.assertIsNotNone(completed.withdrawn_at)
        self.assertEqual(open_progress.status, AssignmentProgress.Status.WITHDRAWN)
        self.assertTrue(IndependentAttempt.objects.filter(pk=attempt.pk).exists())
        self.assertFalse(GroupMembership.objects.filter(student=self.student).exists())

        self.client.post(reverse("teaching:join"), {"code": self.group.join_code})
        for progress in (completed, open_progress):
            with self.assertRaises(PermissionDenied):
                start_assignment(self.student, progress)

    def test_switch_does_not_transfer_assigned_answers_to_new_teacher(self):
        assignment = self.assign()
        progress = assignment.progress_records.get(student=self.student)
        attempt = IndependentAttempt.objects.create(
            user=self.student, lesson=self.lesson, skill="transfer",
            submitted="This is my room.", outcome="self_reported",
            assignment_progress=progress,
        )
        self.client.force_login(self.student)
        self.client.post(reverse("teaching:join"), {"code": self.other_group.join_code})
        progress.refresh_from_db()
        self.assertEqual(progress.status, AssignmentProgress.Status.WITHDRAWN)
        for teacher in (self.teacher, self.other_teacher):
            self.client.force_login(teacher)
            self.assertEqual(
                self.client.get(reverse("teaching:review", args=[attempt.pk])).status_code, 404,
            )
            self.assertNotContains(
                self.client.get(reverse("teaching:review_list")), "This is my room.",
            )
        self.other_teacher.teacher_sees_all = True
        self.other_teacher.save(update_fields=["teacher_sees_all"])
        self.client.force_login(self.other_teacher)
        self.assertEqual(
            self.client.get(reverse("teaching:review", args=[attempt.pk])).status_code, 200,
        )

    def batch_form(self, page, *, progress=None):
        return {
            "action": "batch", "assistance": "no_help",
            "batch_token": page.context["batch_token"],
            "transfer_variant": str(page.context["transfer_variant"]),
            "assignment_id": str(progress.pk) if progress else "",
            "answer_meaning": "Это комната.", "answer_writing": "This is a room.",
            "answer_transfer": "This is my room.",
            "answer_explain": "Перед одним предметом ставлю артикль.",
        }

    def test_repeated_assignments_and_self_study_keep_separate_answer_batches(self):
        first = self.assign().progress_records.get(student=self.student)
        second = self.assign().progress_records.get(student=self.student)
        url = reverse("learning:independent_check", args=[self.lesson.slug])
        first_url, second_url = f"{url}?assignment={first.pk}", f"{url}?assignment={second.pk}"
        self.client.force_login(self.student)
        first_page = self.client.get(first_url)
        second_page = self.client.get(second_url)
        self_page = self.client.get(url)
        for target, page, progress in (
            (first_url, first_page, first),
            (second_url, second_page, second),
            (url, self_page, None),
        ):
            response = self.client.post(target, self.batch_form(page, progress=progress))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                IndependentAttempt.objects.filter(
                    user=self.student, assignment_progress=progress,
                ).count(), 4,
            )

    def test_assignment_context_cannot_be_forged_or_changed_on_submission(self):
        assignment = self.assign()
        own = assignment.progress_records.get(student=self.student)
        foreign = AssignmentProgress.objects.create(
            assignment=assignment, student=self.late_student,
        )
        self.client.force_login(self.student)
        url = reverse("learning:independent_check", args=[self.lesson.slug])
        for pk in (foreign.pk, "invalid"):
            self.assertEqual(self.client.get(f"{url}?assignment={pk}").status_code, 404)
        page = self.client.get(url)
        data = self.batch_form(page, progress=own)
        self.assertEqual(self.client.post(url, data).status_code, 400)
        own_page = self.client.get(f"{url}?assignment={own.pk}")
        data = self.batch_form(own_page)
        self.assertEqual(self.client.post(url, data).status_code, 400)
        self.assertEqual(IndependentAttempt.objects.filter(user=self.student).count(), 0)

    def test_student_dashboard_and_lesson_preserve_explicit_assignment_context(self):
        progress = self.assign().progress_records.get(student=self.student)
        self.client.force_login(self.student)
        dashboard = self.client.get(reverse("learning:dashboard"))
        self.assertContains(dashboard, "Задания учителя")
        open_url = reverse("teaching:assignment_open", args=[progress.pk])
        self.assertContains(dashboard, open_url)
        self.assertEqual(self.client.get(open_url).status_code, 405)
        opened = self.client.post(open_url, follow=True)
        progress.refresh_from_db()
        self.assertEqual(progress.status, AssignmentProgress.Status.IN_PROGRESS)
        check_url = reverse("learning:independent_check", args=[self.lesson.slug])
        self.assertContains(opened, f'{check_url}?assignment={progress.pk}')
        complete_url = reverse("teaching:assignment_complete", args=[progress.pk])
        self.assertContains(opened, complete_url)
        self.client.post(complete_url, {"source": "after_assignment"})
        progress.refresh_from_db()
        timestamp = progress.completed_at
        self.assertEqual(progress.status, AssignmentProgress.Status.COMPLETED)
        self.client.post(complete_url, {"source": "previously_completed"})
        progress.refresh_from_db()
        self.assertEqual(progress.completed_at, timestamp)
        self.assertEqual(progress.completion_source, "after_assignment")
        ordinary = self.client.get(reverse("lessons:detail", args=[self.lesson.slug]))
        self.assertNotContains(ordinary, complete_url)

    def test_foreign_progress_and_withdrawn_progress_cannot_be_changed_by_url(self):
        progress = self.assign().progress_records.get(student=self.student)
        self.client.force_login(self.late_student)
        for name in ("assignment_open", "assignment_complete"):
            url = reverse(f"teaching:{name}", args=[progress.pk])
            self.assertEqual(self.client.post(url, {"source": "after_assignment"}).status_code, 404)
        self.assertEqual(
            self.client.get(reverse("teaching:assignment_history", args=[progress.pk])).status_code, 404,
        )
        self.client.force_login(self.student)
        self.client.post(reverse("teaching:leave"))
        for name in ("assignment_open", "assignment_complete"):
            url = reverse(f"teaching:{name}", args=[progress.pk])
            self.assertEqual(self.client.post(url, {"source": "after_assignment"}).status_code, 404)
        page = self.client.get(reverse("learning:dashboard"))
        self.assertContains(page, "Снято после выхода")
        self.assertNotContains(page, reverse("teaching:assignment_open", args=[progress.pk]))

    def test_student_keeps_review_after_exit_and_review_is_specific_to_one_answer(self):
        first = self.assign().progress_records.get(student=self.student)
        second = self.assign().progress_records.get(student=self.student)
        attempts = [
            IndependentAttempt.objects.create(
                user=self.student, lesson=self.lesson, skill="transfer",
                submitted="This is my room.", outcome="self_reported", assignment_progress=p,
            )
            for p in (first, second)
        ]
        self.client.force_login(self.teacher)
        response = self.client.post(reverse("teaching:review", args=[attempts[0].pk]), {
            "teacher_verdict": "meets_task", "teacher_note": "Вы хорошо передали смысл этой ситуации.",
            "rubric_meaning": "yes", "rubric_form": "yes", "rubric_context": "yes",
        })
        self.assertEqual(response.status_code, 302)
        attempts[1].refresh_from_db()
        self.assertEqual(attempts[1].teacher_verdict, IndependentAttempt.TeacherVerdict.UNREVIEWED)
        self.client.force_login(self.student)
        self.client.post(reverse("teaching:leave"))
        history = self.client.get(reverse("learning:independent_check", args=[self.lesson.slug]))
        self.assertContains(history, "Вы хорошо передали смысл этой ситуации.")
        exact_history = self.client.get(reverse("teaching:assignment_history", args=[first.pk]))
        self.assertContains(exact_history, "Вы хорошо передали смысл этой ситуации.")
        self.assertContains(exact_history, "только для чтения")

    def test_teacher_assignment_form_rejects_foreign_group_and_unpublished_lesson(self):
        self.client.force_login(self.teacher)
        url = reverse("teaching:assignment_new")
        page = self.client.get(url)
        self.assertContains(page, self.group.name)
        self.assertNotContains(page, self.other_group.name)
        data = {"group": self.other_group.pk, "lesson": self.lesson.pk, "due_date": ""}
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(LessonAssignment.objects.count(), 0)
        data["group"] = self.group.pk
        self.lesson.is_published = False
        self.lesson.save(update_fields=["is_published"])
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(LessonAssignment.objects.count(), 0)
        self.lesson.is_published = True
        self.lesson.save(update_fields=["is_published"])
        data["due_date"] = "2026-11-05"
        self.assertEqual(self.client.post(url, data).status_code, 302)
        assignment = LessonAssignment.objects.get()
        self.assertEqual(assignment.teacher, self.teacher)
        self.assertEqual(assignment.due_date, date(2026, 11, 5))
        self.assertEqual(list(assignment.progress_records.values_list("student_id", flat=True)), [self.student.pk])

    def test_teacher_lists_repeated_assignments_but_cannot_read_foreign_assignment(self):
        first, second = self.assign(), self.assign()
        self.client.force_login(self.teacher)
        page = self.client.get(reverse("teaching:assignments"))
        for assignment in (first, second):
            self.assertContains(page, reverse("teaching:assignment", args=[assignment.pk]))
        detail_url = reverse("teaching:assignment", args=[first.pk])
        self.assertContains(self.client.get(detail_url), self.student.email)
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.other_teacher.teacher_sees_all = True
        self.other_teacher.save(update_fields=["teacher_sees_all"])
        self.assertEqual(self.client.get(detail_url).status_code, 200)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(detail_url).status_code, 403)
        self.assertEqual(self.client.get(reverse("teaching:assignment_new")).status_code, 403)

    def test_attention_separates_overdue_from_pending_review_of_completed_work(self):
        overdue = self.assign(due_date=date(2026, 11, 4)).progress_records.get(student=self.student)
        due_today = self.assign(due_date=date(2026, 11, 5)).progress_records.get(student=self.student)
        no_deadline = self.assign().progress_records.get(student=self.student)
        completed = complete_assignment(
            self.student, self.assign(due_date=date(2026, 11, 4)).progress_records.get(student=self.student),
        )
        pending = IndependentAttempt.objects.create(
            user=self.student, lesson=self.lesson, skill="transfer",
            submitted="This is my room.", outcome="self_reported", assignment_progress=completed,
        )
        self.client.force_login(self.teacher)
        now = datetime(2026, 11, 5, 12, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        with patch("apps.teaching.assignments.timezone.now", return_value=now):
            page = self.client.get(reverse("teaching:dashboard"))
        self.assertEqual([p.pk for p in page.context["overdue_assignments"]], [overdue.pk])
        self.assertNotIn(due_today, page.context["overdue_assignments"])
        self.assertNotIn(no_deadline, page.context["overdue_assignments"])
        self.assertContains(page, reverse("teaching:review", args=[pending.pk]))
        self.assertContains(page, "Требуют внимания")
        self.client.force_login(self.student)
        self.client.post(reverse("teaching:leave"))
        self.client.force_login(self.teacher)
        detail = self.client.get(reverse("teaching:assignment", args=[overdue.assignment_id]))
        self.assertNotContains(detail, self.student.email)

    def test_complete_overdue_list_is_paginated_and_scoped_to_teacher(self):
        for _ in range(21):
            self.assign(due_date=date(2026, 1, 1))
        self.client.force_login(self.teacher)
        url = reverse("teaching:overdue_assignments")
        first, second = self.client.get(url), self.client.get(f"{url}?page=2")
        self.assertEqual(len(first.context["page"]), 20)
        self.assertEqual(len(second.context["page"]), 1)
        self.client.force_login(self.other_teacher)
        self.assertEqual(len(self.client.get(url).context["page"]), 0)

    def test_post_actions_require_csrf_and_answer_context_cannot_be_swapped(self):
        first = self.assign().progress_records.get(student=self.student)
        second = self.assign().progress_records.get(student=self.student)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.student)
        self.assertEqual(
            protected.post(reverse("teaching:assignment_complete", args=[first.pk]), {
                "source": "previously_completed",
            }).status_code, 403,
        )
        self.client.force_login(self.student)
        url = reverse("learning:independent_check", args=[self.lesson.slug])
        first_page = self.client.get(f"{url}?assignment={first.pk}")
        self.client.get(f"{url}?assignment={second.pk}")
        data = self.batch_form(first_page, progress=second)
        response = self.client.post(f"{url}?assignment={second.pk}", data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.student).exists())
