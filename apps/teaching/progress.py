"""Сводка прогресса учеников для кабинета учителя. Только чтение.

Для списка сводки считаются пачкой: несколько общих запросов на страницу,
а не по четыре на каждого ученика.
"""
from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Max, Q
from django.utils import timezone

from apps.learning.models import ExerciseAttempt, Status, UnitProgress, WeekGoal

STRONG = (Status.INDEPENDENT_USE, Status.ACTIVE)


@dataclass
class Summary:
    units_started: int = 0
    units_strong: int = 0
    units_due: int = 0
    attempts_30d: int = 0
    correct_share_30d: int | None = None  # проценты; None — ответов не было
    weeks_done: int = 0
    last_attempt_at: object = None


def summarize_many(students) -> dict[int, Summary]:
    """Сводки для набора учеников за 3 запроса, независимо от их числа."""
    ids = [s.pk for s in students]
    out = {pk: Summary() for pk in ids}
    if not ids:
        return out
    now = timezone.now()
    for row in (UnitProgress.objects.filter(user_id__in=ids).values("user_id").annotate(
            started=Count("pk"), strong=Count("pk", filter=Q(status__in=STRONG)),
            due=Count("pk", filter=Q(next_review_at__lte=now)))):
        s = out[row["user_id"]]
        s.units_started, s.units_strong, s.units_due = row["started"], row["strong"], row["due"]
    month = now - timedelta(days=30)
    for row in (ExerciseAttempt.objects.filter(user_id__in=ids).values("user_id").annotate(
            total=Count("pk", filter=Q(created_at__gte=month)),
            correct=Count("pk", filter=Q(created_at__gte=month, is_correct=True)),
            last=Max("created_at"))):
        s = out[row["user_id"]]
        s.attempts_30d, s.last_attempt_at = row["total"], row["last"]
        s.correct_share_30d = round(100 * row["correct"] / row["total"]) if row["total"] else None
    for row in (WeekGoal.objects.filter(user_id__in=ids, status=WeekGoal.GoalStatus.DONE)
                .values("user_id").annotate(n=Count("pk"))):
        out[row["user_id"]].weeks_done = row["n"]
    return out


def summarize(student) -> Summary:
    return summarize_many([student])[student.pk]


def recent_attempts(student, limit: int = 20):
    return (ExerciseAttempt.objects.filter(user=student)
            .select_related("exercise__lesson")[:limit])


def week_goals(student):
    return (WeekGoal.objects.filter(user=student)
            .select_related("week__level").order_by("week__level__order", "week__number"))
