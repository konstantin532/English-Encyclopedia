"""Optional original A1 interactive scenes: lessons 1–24 only.

Only reads vetted local curriculum JSON. Does not modify user progress, lesson
records, or the canonical lesson content.
"""
import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET

MAX_TOPIC = 24
TOPIC_FILES = (
    "topics_01_08.json",
    "topics_09_13.json",
    "topics_14_18.json",
    "topics_19_20.json",
    "topics_21_22.json",
    "topics_23_24.json",
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
    repairs = []
    for filename in ("error_repairs_01_18.json", "error_repairs_19_20.json", "error_repairs_21_22.json", "error_repairs_23_24.json"):
        repairs.extend(json.loads((root / filename).read_text(encoding="utf-8")))
    if len(repairs) != MAX_TOPIC or {r["n"] for r in repairs} != expected:
        raise ValueError("A1 error-repair exercises must cover exactly lessons 1-24")
    for repair in repairs:
        topics[repair["n"]]["repair"] = {
            "wrong": repair["wrong"], "correct": repair["correct"],
            "hint": repair["hint"], "reason": repair["reason"],
            "alternatives": repair.get("alternatives", []),
        }

    # Six original contextual missions per lesson. They supplement, rather than
    # overwrite, the canonical seven-layer learning material and original lab.
    scenarios = []
    for filename in (
        "scenarios_01_06.json", "scenarios_07_12.json", "scenarios_13_18.json",
        "scenarios_19_20.json", "scenarios_21_22.json", "scenarios_23_24.json"
    ):
        scenarios.extend(json.loads((root / filename).read_text(encoding="utf-8")))
    if len(scenarios) != MAX_TOPIC or {row["n"] for row in scenarios} != expected:
        raise ValueError("Scenario catalog must cover lessons 1–24 exactly once")
    for block in scenarios:
        missions = block["missions"]
        twists = block["twists"]
        if (
            len(missions) != 6 or [m["id"] for m in missions] != [1, 2, 3, 4, 5, 6]
            or len(twists) != 2
            or not all(all(isinstance(m[k], str) and m[k].strip()
                           for k in ("title", "scene", "prompt", "example", "coach"))
                       for m in missions)
            or not all(all(isinstance(t[k], str) and t[k].strip()
                           for k in ("scene", "example")) for t in twists)
        ):
            raise ValueError(f"Invalid scenarios for A1 lesson {block['n']}")
        topics[block["n"]]["missions"] = missions
        topics[block["n"]]["twists"] = twists
    return topics


def active_topics():
    """Return the bounded 24-item supplement without changing canonical lessons."""
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
    raw_start = request.GET.get("mission", "1")
    try:
        start_mission = int(raw_start)
    except (ValueError, TypeError):
        start_mission = 1
    if start_mission < 1 or start_mission > 6:
        start_mission = 1
    return render(request, "core/a1_active_topic.html", {
        "start_mission": start_mission,
        "topic": item,
        "topic_limit": MAX_TOPIC,
        "topic_previous": number - 1 if number > 1 else None,
        "topic_next": number + 1 if number < MAX_TOPIC else None,
    })
