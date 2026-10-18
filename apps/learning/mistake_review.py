"""Editor-written alternative questions for delayed A1 concept review.

Question options are shown only when their two-day due date is reached.
Answers stay server-side until the learner makes an independent choice.
"""
import json
from datetime import timedelta
from functools import lru_cache

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.drills.retry_guidance import PILOT_SLUGS
from .models import MistakeReview

DELAY = timedelta(days=2)
COUNT = 5


@lru_cache(maxsize=1)
def question_bank():
    root = settings.CONTENT_DIR / "manifests"
    bank = {}
    for number in range(1, 9):
        packet = json.loads((root / f"a1_delayed_review_{number:02d}.json").read_text(encoding="utf-8"))
        for slug, problems in packet.items():
            if slug in bank:
                raise ValueError(f"Повтор раздела: {slug}")
            bank[slug] = problems
    if set(bank) != PILOT_SLUGS:
        raise ValueError("Ожидаются ровно восемь уроков A1")
    for slug, exercises in bank.items():
        expected = {"a1-nouns-first-words": 4, "a1-verb-be": 5,
                    "a1-determiners-a-the-this-my": 6, "a1-have-like-can-do": 6,
                    "a1-cafe-order": 6, "a1-numbers-1-20": 4,
                    "a1-family-photo": 6, "a1-family-possession": 6}[slug]
        if set(exercises) != {str(i) for i in range(1, expected + 1)}:
            raise ValueError(f"Не все упражнения покрыты: {slug}")
        for number, variants in exercises.items():
            if len(variants) != COUNT:
                raise ValueError(f"Нужно 5 новых заданий: {slug} #{number}")
            for row in variants:
                if (len(row) != 4 or not all(isinstance(x, str) for x in row[:2])
                        or not row[0].strip() or not isinstance(row[2], list)
                        or len(row[2]) != 3 or not all(isinstance(x, str) and x.strip() for x in row[2])
                        or len(set(row[2])) != 3 or type(row[3]) is not int or row[3] not in range(3)):
                    raise ValueError(f"Неверная карточка: {slug} #{number}")
    return bank


def variants_for(exercise):
    return question_bank().get(exercise.lesson.slug, {}).get(str(exercise.order), [])


@transaction.atomic
def schedule_review(user, exercise, now=None):
    """The first confirmed mistake schedules the five new questions at +48h.

    Repeated mistakes before that date do not postpone the already-scheduled work.
    """
    if not user.is_authenticated or not variants_for(exercise):
        return None
    now = now or timezone.now()
    item, created = MistakeReview.objects.select_for_update().get_or_create(
        user=user, exercise=exercise,
        defaults={"due_at": now + DELAY},
    )
    if not created and item.completed_at is not None:
        item.due_at = now + DELAY
        item.current_index = 0
        item.correct_count = 0
        item.completed_at = None
        item.save(update_fields=["due_at", "current_index", "correct_count", "completed_at", "updated_at"])
    return item.due_at


def due_reviews(user, now=None):
    now = now or timezone.now()
    return (MistakeReview.objects.filter(user=user, completed_at__isnull=True, due_at__lte=now,
                                         exercise__lesson__is_published=True)
            .select_related("exercise__lesson").order_by("due_at", "pk"))
