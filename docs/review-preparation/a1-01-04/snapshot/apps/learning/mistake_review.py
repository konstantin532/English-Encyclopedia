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
from .micro_review import micro_bank

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
    # The first eight lessons have five individually authored prompts per
    # specific error. For the remaining twenty lessons, five distinct *theme*
    # questions are shared by the six source exercises of that lesson.
    # That is useful practice, but is not a precise diagnosis of each error.
    for start in (9, 13, 17, 21, 25):
        end = start + 3
        path = root / f"a1_delayed_review_topics_{start:02d}_{end:02d}.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        if len(packet) != 4:
            raise ValueError(f"Ожидаются четыре темы в {path.name}")
        for slug, cards in packet.items():
            if slug in bank:
                raise ValueError(f"Повтор раздела: {slug}")
            if len(cards) != COUNT:
                raise ValueError(f"Ожидаются пять вопросов по теме: {slug}")
            bank[slug] = {str(order): cards for order in range(1, 7)}

    # Replace shared lesson topics with carefully targeted five-case packs
    # only where the editorial micro-skill data has been completed.
    for slug, cases in micro_bank().items():
        if slug not in bank or slug in (
            "a1-nouns-first-words", "a1-verb-be",
            "a1-determiners-a-the-this-my", "a1-have-like-can-do",
            "a1-cafe-order", "a1-numbers-1-20",
            "a1-family-photo", "a1-family-possession",
        ):
            raise ValueError(f"Invalid micro-skill override: {slug}")
        bank[slug] = cases

    if set(bank) != PILOT_SLUGS or len(bank) != 28:
        raise ValueError("Ожидаются ровно двадцать восемь уроков A1")
    counts = {"a1-nouns-first-words": 4, "a1-verb-be": 5,
              "a1-numbers-1-20": 4}
    for slug, exercises in bank.items():
        expected = counts.get(slug, 6)
        if set(exercises) != {str(i) for i in range(1, expected + 1)}:
            raise ValueError(f"Не все упражнения покрыты: {slug}")
        for number, variants in exercises.items():
            if len(variants) != COUNT or len({row[0] for row in variants}) != COUNT:
                raise ValueError(f"Нужно 5 разных вопросов: {slug} #{number}")
            for row in variants:
                if (len(row) not in (4, 5) or not all(isinstance(x, str) for x in row[:2])
                        or not row[0].strip() or not isinstance(row[2], list)
                        or len(row[2]) != 3 or not all(isinstance(x, str) and x.strip() for x in row[2])
                        or len(set(row[2])) != 3 or type(row[3]) is not int or row[3] not in range(3)
                        or (len(row) == 5 and not isinstance(row[4], str))):
                    raise ValueError(f"Неверная карточка: {slug} #{number}")
    return bank


def _check_cards(slug, cards):
    if len(cards) != COUNT or len({row[0] for row in cards}) != COUNT:
        raise ValueError(f"Нужно 5 разных вопросов: {slug}")
    for row in cards:
        if (len(row) not in (4, 5) or not all(isinstance(x, str) for x in row[:2]) or not row[0].strip()
                or not isinstance(row[2], list) or len(row[2]) != 3 or len(set(row[2])) != 3
                or not all(isinstance(x, str) and x.strip() for x in row[2])
                or type(row[3]) is not int or row[3] not in range(3) or (len(row) == 5 and not isinstance(row[4], str))):
            raise ValueError(f"Неверная карточка: {slug}")


@lru_cache(maxsize=1)
def level_bank():
    """Отложенные вопросы уроков после A1 (A1+ и дальше): пять вопросов по теме урока на все его задания.

    Банк A1 (question_bank) остаётся ровно на 28 уроков; новые уровни живут в своих файлах.
    """
    bank = {}
    for path in sorted((settings.CONTENT_DIR / "manifests").glob("a1p_delayed_review*.json")):
        for slug, cards in json.loads(path.read_text(encoding="utf-8")).items():
            if slug in bank or slug in PILOT_SLUGS:
                raise ValueError(f"Повтор раздела: {slug}")
            _check_cards(slug, cards)
            bank[slug] = {str(order): cards for order in range(1, 7)}
    return bank


def variants_for(exercise):
    slug, order = exercise.lesson.slug, str(exercise.order)
    return question_bank().get(slug, {}).get(order) or level_bank().get(slug, {}).get(order, [])


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


def available_reviews(user):
    """Withdraw archived/unpublished tasks without deleting learner history.

    Related-model joins do not apply Exercise's active-only default manager.
    Every queue, badge and submission must use the same explicit boundary.
    """
    return MistakeReview.objects.filter(
        user=user, completed_at__isnull=True,
        exercise__is_archived=False, exercise__lesson__is_published=True,
    )


def due_reviews(user, now=None):
    now = now or timezone.now()
    return (available_reviews(user).filter(due_at__lte=now)
            .select_related("exercise__lesson").order_by("due_at", "pk"))
