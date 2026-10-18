"""Editor-authored retry pointers for the four A1 foundation lessons.

These prompts identify what to review, not what the user's free response
actually means. Never infer semantic incorrectness from a model mismatch.
"""
import json
from functools import lru_cache

from django.conf import settings

from apps.drills.models import Exercise

PILOT_SLUGS = frozenset({
    "a1-nouns-first-words",
    "a1-verb-be",
    "a1-determiners-a-the-this-my",
    "a1-have-like-can-do",
    "a1-cafe-order",
    "a1-numbers-1-20",
})


@lru_cache(maxsize=1)
def _catalog():
    path = settings.CONTENT_DIR / "manifests" / "a1_retry_guidance.json"
    return json.loads(path.read_text(encoding="utf-8"))


def is_pilot_exercise(exercise):
    return exercise.lesson.slug in PILOT_SLUGS and exercise.lesson.level.code == "A1"


def is_open_pilot_response(exercise):
    # Short, fixed-choice and word-order tasks remain objectively checkable.
    # Transfer prompts accept creative sentences; a finite answer key is only
    # a collection of examples, not a complete natural-language validator.
    return (is_pilot_exercise(exercise)
            and exercise.kind == Exercise.Kind.FILL
            and exercise.stage == Exercise.Stage.TRANSFER)


def retry_guidance(exercise, submitted):
    if not is_pilot_exercise(exercise):
        return ""
    entry = _catalog().get(exercise.lesson.slug, {}).get(str(exercise.order), {})
    options = entry.get("choices", {}) if exercise.kind == Exercise.Kind.CHOICE else {}
    normalized = Exercise.normalize(submitted)
    for candidate, explanation in options.items():
        if Exercise.normalize(candidate) == normalized:
            return explanation
    return entry.get("focus", "")
