from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.drills.models import Exercise
from apps.lexicon.models import LexicalUnit

# Интервалы повторения (раздел 11): сразу, через день, 3–4 дня, неделя, две недели.
REVIEW_INTERVALS_DAYS = (0, 1, 3, 7, 14)


class Status(models.TextChoices):
    NEW = "new", "Новое"
    RECOGNITION = "recognition", "Узнаю"
    GUIDED_USE = "guided_use", "С подсказкой"
    INDEPENDENT_USE = "independent_use", "Сам"
    ACTIVE = "active", "Активный словарь"
    REVIEW_DUE = "review_due", "Пора повторить"


STATUS_LADDER = [Status.NEW, Status.RECOGNITION, Status.GUIDED_USE, Status.INDEPENDENT_USE, Status.ACTIVE]


class UnitProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="unit_progress")
    unit = models.ForeignKey(LexicalUnit, on_delete=models.CASCADE, related_name="progress")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    stage = models.PositiveSmallIntegerField(default=0, help_text="Ступень интервала 0–4")
    next_review_at = models.DateTimeField(null=True, blank=True)
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)
    contexts_used = models.JSONField(default=list, blank=True, help_text="Разные конструкции, где единица употреблена")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "unit"], name="uniq_progress_per_unit")]
        indexes = [models.Index(fields=["user", "next_review_at"])]

    def register(self, correct: bool, context: str = "") -> None:
        now = timezone.now()
        if correct:
            self.correct_count += 1
            if context and context not in self.contexts_used:
                self.contexts_used = [*self.contexts_used, context]
            self.stage = min(self.stage + 1, len(REVIEW_INTERVALS_DAYS) - 1)
            ladder_pos = STATUS_LADDER.index(self.status) if self.status in STATUS_LADDER else 1
            next_status = STATUS_LADDER[min(ladder_pos + 1, len(STATUS_LADDER) - 1)]
            # В активный словарь — только после трёх разных конструкций.
            if next_status == Status.ACTIVE and len(self.contexts_used) < 3:
                next_status = Status.INDEPENDENT_USE
            self.status = next_status
        else:
            self.wrong_count += 1
            self.stage = max(self.stage - 1, 0)
            if self.status == Status.ACTIVE:
                self.status = Status.INDEPENDENT_USE
        self.next_review_at = now + timedelta(days=REVIEW_INTERVALS_DAYS[self.stage])


class ExerciseAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="attempts")
    answer = models.CharField(max_length=200)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]
