"""Rules for one issued lesson, never inferred from unrelated learning history."""
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .access import can_teach, learners
from .models import AssignmentProgress, GroupMembership, LessonAssignment, StudyGroup

OPEN_STATUSES = (AssignmentProgress.Status.NOT_STARTED, AssignmentProgress.Status.IN_PROGRESS)
MOSCOW = ZoneInfo("Europe/Moscow")


def assignment_is_overdue(progress, *, now=None):
    due_date = progress.assignment.due_date
    return bool(
        due_date and progress.status in OPEN_STATUSES
        and due_date < timezone.localdate(now or timezone.now(), timezone=MOSCOW)
    )


@transaction.atomic
def create_lesson_assignment(*, teacher, group, lesson, due_date=None):
    group = StudyGroup.objects.select_for_update().get(pk=group.pk)
    if not can_teach(teacher) or group.teacher_id != teacher.pk:
        raise PermissionDenied
    if not lesson.is_published:
        raise ValidationError("Назначить можно только опубликованный урок.")
    assignment = LessonAssignment.objects.create(
        teacher=teacher, group=group, lesson=lesson, due_date=due_date,
    )
    AssignmentProgress.objects.bulk_create([
        AssignmentProgress(assignment=assignment, student_id=student_id)
        for student_id in learners().filter(
            group_membership__group=group,
        ).values_list("pk", flat=True)
    ])
    return assignment


def lock_writable_progress(student, progress):
    # The same user lock serializes completion, answer submission and group exit.
    # NO KEY UPDATE also permits FK inserts while assignment creation holds the group lock.
    get_user_model().objects.select_for_update(no_key=True).get(pk=student.pk)
    current = AssignmentProgress.objects.select_for_update().select_related("assignment").get(pk=progress.pk)
    if (current.student_id != student.pk or current.withdrawn_at is not None
            or current.status == AssignmentProgress.Status.WITHDRAWN
            or not GroupMembership.objects.filter(
                student=student, group_id=current.assignment.group_id,
            ).exists()):
        raise PermissionDenied
    return current


@transaction.atomic
def start_assignment(student, progress, *, now=None):
    progress = lock_writable_progress(student, progress)
    if progress.status == AssignmentProgress.Status.NOT_STARTED:
        progress.status = AssignmentProgress.Status.IN_PROGRESS
        progress.started_at = now or timezone.now()
        progress.save(update_fields=["status", "started_at"])
    return progress


@transaction.atomic
def complete_assignment(student, progress, *, previously_completed=False, now=None):
    progress = lock_writable_progress(student, progress)
    if progress.status != AssignmentProgress.Status.COMPLETED:
        progress.status = AssignmentProgress.Status.COMPLETED
        progress.completed_at = now or timezone.now()
        progress.completion_source = (
            AssignmentProgress.CompletionSource.PREVIOUSLY_COMPLETED if previously_completed
            else AssignmentProgress.CompletionSource.AFTER_ASSIGNMENT
        )
        progress.save(update_fields=["status", "completed_at", "completion_source"])
    return progress


def withdraw_assignments_for_group(student, group, *, now=None):
    """Caller holds the user's lock and the old group's lock until membership changes."""
    records = AssignmentProgress.objects.filter(
        student=student, assignment__group=group, withdrawn_at__isnull=True,
    )
    # Completed records keep their status, but also become permanently read-only.
    records.filter(status__in=OPEN_STATUSES).update(status=AssignmentProgress.Status.WITHDRAWN)
    records.update(withdrawn_at=now or timezone.now())


@transaction.atomic
def change_student_group(student, group=None):
    """Serialize joins/exits with assignment creation and learner writes."""
    get_user_model().objects.select_for_update(no_key=True).get(pk=student.pk)
    membership = GroupMembership.objects.filter(student=student).first()
    group_ids = {g for g in (membership.group_id if membership else None, group.pk if group else None) if g}
    list(StudyGroup.objects.select_for_update().filter(pk__in=group_ids).order_by("pk"))
    if membership and group and membership.group_id == group.pk:
        return
    if membership:
        withdraw_assignments_for_group(student, membership.group)
    if group:
        GroupMembership.objects.update_or_create(student=student, defaults={"group": group})
    elif membership:
        membership.delete()


def student_assignment(student, pk, *, lesson=None):
    """A writable context must be explicit, owned, and still in its original group."""
    if not student.is_authenticated:
        raise Http404
    try:
        pk = int(pk)
    except (TypeError, ValueError):
        raise Http404
    records = AssignmentProgress.objects.select_related("assignment__lesson", "assignment__group").filter(
        student=student, withdrawn_at__isnull=True,
        assignment__group__memberships__student=student,
    ).exclude(status=AssignmentProgress.Status.WITHDRAWN)
    if lesson is not None:
        records = records.filter(assignment__lesson=lesson)
    return get_object_or_404(records, pk=pk)


def student_assignment_cards(student):
    group_id = GroupMembership.objects.filter(student=student).values_list("group_id", flat=True).first()
    active, history = [], []
    records = AssignmentProgress.objects.filter(student=student).select_related(
        "assignment__lesson", "assignment__group",
    ).order_by("-assignment__assigned_at", "-pk")
    for progress in records:
        writable = progress.withdrawn_at is None and progress.assignment.group_id == group_id
        row = {"progress": progress, "overdue": assignment_is_overdue(progress), "writable": writable}
        (active if writable and progress.status in OPEN_STATUSES else history).append(row)
    return active, history


def teacher_assignments(teacher):
    records = LessonAssignment.objects.select_related("lesson", "group")
    if teacher.is_superuser or teacher.teacher_sees_all:
        return records
    return records.filter(group__teacher=teacher)


def teacher_assignment_progress(teacher):
    records = AssignmentProgress.objects.filter(
        assignment__in=teacher_assignments(teacher), student__in=learners(),
    ).select_related("student", "assignment__lesson", "assignment__group")
    if not (teacher.is_superuser or teacher.teacher_sees_all):
        records = records.filter(
            withdrawn_at__isnull=True,
            assignment__group__memberships__student=F("student_id"),
        )
    return records


def overdue_for_teacher(teacher):
    return teacher_assignment_progress(teacher).filter(
        status__in=OPEN_STATUSES, withdrawn_at__isnull=True,
        assignment__due_date__lt=timezone.localdate(timezone.now(), timezone=MOSCOW),
    ).order_by("assignment__due_date", "pk")
