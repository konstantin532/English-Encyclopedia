"""A1 understanding aids and no-options checks; not a language proficiency certificate."""
import json
from functools import lru_cache

from django.conf import settings
from apps.drills.retry_guidance import PILOT_SLUGS

FIELDS = ("plain", "why", "pattern", "mistake", "fix", "example", "translation")
SKILLS = ("meaning", "writing", "transfer")


def quality_gates(document):
    """15 separate automated editorial STRUCTURAL gates, not 15 human reviews."""
    lessons = document.get("lessons", [])
    slugs = [x.get("slug") for x in lessons]
    all_tasks = [t for x in lessons for t in x.get("tasks", {}).values()]
    flat = [x.get(k, "") for x in lessons for k in FIELDS]
    expected = set(PILOT_SLUGS)
    return {
        "01_manifest_version": document.get("version") == 1,
        "02_only_a1": document.get("level") == "A1",
        "03_exactly_28_guides": len(lessons) == 28,
        "04_unique_slugs": len(set(slugs)) == len(slugs),
        "05_known_lesson_slugs": set(slugs) == expected,
        "06_all_guide_sections": all(all(isinstance(x.get(k), str) and x[k].strip()
                                         for k in FIELDS) for x in lessons),
        "07_simple_explanation_length": all(18 <= len(x["plain"]) <= 260 for x in lessons),
        "08_explicit_reason_length": all(18 <= len(x["why"]) <= 330 for x in lessons),
        "09_concrete_pattern": all(12 <= len(x["pattern"]) <= 180 for x in lessons),
        "10_common_mistake_and_fix": all(x["mistake"] != x["fix"]
                                         and len(x["fix"]) >= 18 for x in lessons),
        "11_examples_not_empty": all(x["example"] and x["translation"] for x in lessons),
        "12_three_distinct_skills": all(set(x.get("tasks", {})) == set(SKILLS) for x in lessons),
        "13_prompts_no_word_bank": all(not any(k in t for k in ("options", "choices", "word_bank"))
                                       for t in all_tasks),
        "14_answer_keys_only_for_narrow_tasks": all(
            all(isinstance(x["tasks"][k].get("accepted"), list)
                and x["tasks"][k]["model"] in x["tasks"][k]["accepted"]
                and x["tasks"][k]["prompt"].strip()
                for k in ("meaning", "writing"))
            and "accepted" not in x["tasks"]["transfer"]
            and x["tasks"]["transfer"]["prompt"].strip()
            and x["tasks"]["transfer"]["model"].strip()
            for x in lessons),
        "15_bounds_and_no_model_in_prompt": all(
            all(isinstance(t.get("prompt"), str) and isinstance(t.get("model"), str)
                and 12 <= len(t["prompt"]) <= 600 and 1 <= len(t["model"]) <= 400
                and t["prompt"].strip().casefold() != t["model"].strip().casefold()
                for t in x["tasks"].values()) for x in lessons),
    }


@lru_cache(maxsize=1)
def understanding_bank():
    path = settings.CONTENT_DIR / "manifests" / "a1_understanding_checks.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    gates = quality_gates(data)
    failures = [name for name, passed in gates.items() if not passed]
    if failures:
        raise ValueError("A1 clarity / independent assessment checks failed: " + ", ".join(failures))
    return {row["slug"]: row for row in data["lessons"]}


def get_guide(slug):
    return understanding_bank().get(slug)


def model_agreement(task, submitted):
    """Only proof of a known phrase match, NEVER proof that other phrasings are wrong."""
    from apps.drills.models import Exercise
    answer = Exercise.normalize(submitted)
    return bool(answer and answer in {
        Exercise.normalize(s) for s in task.get("accepted", [])
    })
