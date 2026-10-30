"""Сводка прогресса ученика для кабинета учителя. Только чтение."""
from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.learning.models import ExerciseAttempt, Status, UnitProgress, WeekGoal

STRONG = (Status.INDEPENDENT_USE, Status.ACTIVE)


@dataclass
class Summary:
    units_started: int
    units_strong: int
    units_due: int
    attempts_30d: int
    correct_share_30d: int | None  # проценты; None — ответов не было
    weeks_done: int
    last_attempt_at: object


def summarize(student) -> Summary:
    now = timezone.now()
    units = UnitProgress.objects.filter(user=student).aggregate(
        started=Count("pk"),
        strong=Count("pk", filter=Q(status__in=STRONG)),
        due=Count("pk", filter=Q(next_review_at__lte=now)),
    )
    month = ExerciseAttempt.objects.filter(user=student, created_at__gte=now - timedelta(days=30))
    attempts = month.aggregate(total=Count("pk"), correct=Count("pk", filter=Q(is_correct=True)))
    last = ExerciseAttempt.objects.filter(user=student).values_list("created_at", flat=True).first()
    return Summary(
        units_started=units["started"],
        units_strong=units["strong"],
        units_due=units["due"],
        attempts_30d=attempts["total"],
        correct_share_30d=round(100 * attempts["correct"] / attempts["total"]) if attempts["total"] else None,
        weeks_done=WeekGoal.objects.filter(user=student, status=WeekGoal.GoalStatus.DONE).count(),
        last_attempt_at=last,
    )


def recent_attempts(student, limit: int = 20):
    return (ExerciseAttempt.objects.filter(user=student)
            .select_related("exercise__lesson")[:limit])


def week_goals(student):
    return (WeekGoal.objects.filter(user=student)
            .select_related("week__level").order_by("week__level__order", "week__number"))
