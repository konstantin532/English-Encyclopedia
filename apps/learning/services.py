from dataclasses import dataclass, field
from datetime import timedelta

from django.db.models import Prefetch
from django.urls import reverse
from django.utils import timezone

from apps.drills.models import Exercise

from .models import ExerciseAttempt, UnitProgress, MistakeReview
from .trainer_state import serialized
from .trainer_service import legacy_managed_units


@serialized
def record_attempt(user, exercise: Exercise, answer: str, *, delay_wrong_days: int = 0) -> bool:
    correct = exercise.is_correct(answer)
    if user.is_authenticated:
        ExerciseAttempt.objects.create(user=user, exercise=exercise, answer=answer[:200], is_correct=correct)
        context = f"{exercise.lesson.slug}#{exercise.order}"
        managed = legacy_managed_units(user)
        for unit in exercise.units.all():
            if unit.uid in managed:
                continue
            progress, _ = UnitProgress.objects.select_for_update().get_or_create(user=user, unit=unit)
            progress.register(correct, context)
            if not correct and delay_wrong_days:
                # Do not surface the just-missed lesson question again immediately.
                progress.next_review_at = timezone.now() + timedelta(days=delay_wrong_days)
            progress.save()
    return correct


@serialized
def record_practice(user, item) -> None:
    """Верный перевод — свежее свидетельство самостоятельного употребления слов урока."""
    if not user.is_authenticated:
        return
    context = f"{item.lesson.slug}#t{item.order}"
    managed = legacy_managed_units(user)
    for unit in item.units.all():
        if unit.uid in managed:
            continue
        progress, _ = UnitProgress.objects.select_for_update().get_or_create(user=user, unit=unit)
        progress.register(True, context, mode="independent")  # перевод без вариантов — самостоятельный ответ
        progress.save()


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
    available = Exercise.objects.filter(lesson__is_published=True).select_related("lesson")
    return (UnitProgress.objects.filter(user=user, next_review_at__lte=timezone.now())
            .exclude(unit__uid__in=legacy_managed_units(user))
            .select_related("unit")
            .prefetch_related(Prefetch("unit__exercises", queryset=available))
            .order_by("next_review_at"))


def build_review(user) -> list:
    """Задания на повторение: упражнение урока, если ещё не решено правильно, иначе карточка вспоминания."""
    items, used = [], set()
    solved = set(ExerciseAttempt.objects.filter(user=user, is_correct=True).values_list("exercise_id", flat=True))
    # A recent A1 error gets five different questions after two days.
    # The same failed question is withheld from ordinary review until those
    # alternative questions are complete.
    reserved = set(MistakeReview.objects.filter(
        user=user, completed_at__isnull=True,
    ).values_list("exercise_id", flat=True))
    for progress in due_progress(user)[:REVIEW_BATCH]:
        exercise = next((e for e in progress.unit.exercises.all()
                         if e.pk not in used and e.pk not in solved and e.pk not in reserved), None)
        if exercise:
            used.add(exercise.pk)
            items.append(exercise)
        else:
            items.append(RecallItem(progress.unit))
    return items


@serialized
def record_recall(user, unit, answer: str) -> bool:
    accepted = [unit.lemma, *(unit.forms or [])]
    correct = Exercise.normalize(answer) in {Exercise.normalize(a) for a in accepted}
    if user.is_authenticated and unit.uid not in legacy_managed_units(user):
        progress, _ = UnitProgress.objects.select_for_update().get_or_create(user=user, unit=unit)
        progress.register(correct, mode="independent")  # вспоминание не считается новой конструкцией
        progress.save()
    return correct

