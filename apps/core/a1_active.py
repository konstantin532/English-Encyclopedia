"""Optional original A1 interactive scenes: lessons 1–18 only.

Only reads vetted local curriculum JSON. Does not modify user progress, lesson
records, or the situation-weeks branch.
"""
import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET

MAX_TOPIC = 18
TOPIC_FILES = (
    "topics_01_08.json",
    "topics_09_13.json",
    "topics_14_18.json",
)


@lru_cache(maxsize=4)
def _load_topics(base_dir: str):
    root = Path(base_dir) / "content" / "active_a1"
    topics = {}
    for filename in TOPIC_FILES:
        for item in json.loads((root / filename).read_text(encoding="utf-8")):
            number = item["n"]
            if number in topics:
                raise ValueError(f"Duplicate active A1 topic: {number}")
            topics[number] = item
    expected = set(range(1, MAX_TOPIC + 1))
    if set(topics) != expected:
        raise ValueError("Active A1 topic catalog is incomplete")
    repairs = json.loads((root / "error_repairs_01_18.json").read_text(encoding="utf-8"))
    if len(repairs) != MAX_TOPIC or {r["n"] for r in repairs} != expected:
        raise ValueError("A1 error-repair exercises must cover exactly lessons 1-18")
    for repair in repairs:
        topics[repair["n"]]["repair"] = {
            "wrong": repair["wrong"], "correct": repair["correct"],
            "hint": repair["hint"], "reason": repair["reason"],
        }
    return topics


def active_topics():
    """Return the bounded 18-item supplement; no data from situation-weeks."""
    return _load_topics(str(settings.BASE_DIR))


@require_GET
def active_a1_topic(request, number: int):
    if number < 1 or number > MAX_TOPIC:
        raise Http404("No such A1 topic")
    item = active_topics()[number]
    # Keep supplemental content in sync with the canonical lesson's publication
    # status. A predictable /lab/a1/N/ URL must not bypass unpublished lessons.
    from apps.lessons.models import Lesson
    if not Lesson.objects.filter(
        slug=item["slug"], level__code="A1", order=number, is_published=True
    ).exists():
        raise Http404("Source lesson is not published")
    return render(request, "core/a1_active_topic.html", {
        "topic": item,
        "topic_previous": number - 1 if number > 1 else None,
        "topic_next": number + 1 if number < MAX_TOPIC else None,
    })
