from dataclasses import dataclass, field

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.drills.models import Exercise

from .models import ExerciseAttempt, UnitProgress


@transaction.atomic
def record_attempt(user, exercise: Exercise, answer: str) -> bool:
    correct = exercise.is_correct(answer)
    if user.is_authenticated:
        ExerciseAttempt.objects.create(user=user, exercise=exercise, answer=answer[:200], is_correct=correct)
        context = f"{exercise.lesson.slug}#{exercise.order}"
        for unit in exercise.units.all():
            progress, _ = UnitProgress.objects.select_for_update().get_or_create(user=user, unit=unit)
            progress.register(correct, context)
            progress.save()
    return correct


REVIEW_BATCH = 10


@dataclass
class RecallItem:
    """Карточка вспоминания: русский перевод → английское слово."""

    unit: object
    kind: str = "fill"
    options: list = field(default_factory=list)
    prompt_en: str = ""

    @property
    def pk(self) -> str:
        return f"r{self.unit.uid}"

    @property
    def prompt_ru(self) -> str:
        return f"Как по-английски «{self.unit.translation_ru}»?"

    @property
    def hint_ru(self) -> str:
        return f"Пример: {self.unit.example_ru}" if self.unit.example_ru else ""

    @property
    def check_url(self) -> str:
        return reverse("api:recall_unit", args=[self.unit.uid])

    def get_stage_display(self) -> str:
        return "Вспомнить слово"


def due_progress(user):
    return (UnitProgress.objects.filter(user=user, next_review_at__lte=timezone.now())
            .select_related("unit").order_by("next_review_at"))


def build_review(user) -> list:
    """Задания на повторение: упражнение урока, если ещё не решено правильно, иначе карточка вспоминания."""
    items, used = [], set()
    solved = set(ExerciseAttempt.objects.filter(user=user, is_correct=True).values_list("exercise_id", flat=True))
    for progress in due_progress(user)[:REVIEW_BATCH]:
        exercise = next((e for e in progress.unit.exercises.filter(lesson__is_published=True)
                         if e.pk not in used and e.pk not in solved), None)
        if exercise:
            used.add(exercise.pk)
            items.append(exercise)
        else:
            items.append(RecallItem(progress.unit))
    return items


def record_recall(user, unit, answer: str) -> bool:
    accepted = [unit.lemma, *(unit.forms or [])]
    correct = Exercise.normalize(answer) in {Exercise.normalize(a) for a in accepted}
    if user.is_authenticated:
        progress, _ = UnitProgress.objects.get_or_create(user=user, unit=unit)
        progress.register(correct)  # вспоминание не считается новой конструкцией
        progress.save()
    return correct

