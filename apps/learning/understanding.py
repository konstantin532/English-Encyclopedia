"""A1 understanding aids and no-options checks; not a language proficiency certificate."""
import json
from functools import lru_cache

from django.conf import settings
from apps.drills.retry_guidance import PILOT_SLUGS

FIELDS = ("plain", "why", "pattern", "mistake", "fix", "example", "translation")
SKILLS = ("meaning", "writing", "transfer", "explain")


def quality_gates(document):
    """15 separate automated editorial STRUCTURAL gates, not 15 human reviews."""
    lessons = document.get("lessons", [])
    slugs = [x.get("slug") for x in lessons]
    all_tasks = [t for x in lessons for t in x.get("tasks", {}).values()]
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
        "11_examples_not_empty": all(
            x["example"] and x["translation"]
            and isinstance(x.get("contrast"), dict)
            and all(isinstance(x["contrast"].get(k), str)
                    and x["contrast"][k].strip()
                    for k in ("a_en", "a_ru", "b_en", "b_ru", "why"))
            and x["contrast"]["a_en"] != x["contrast"]["b_en"]
            and len(x["contrast"]["why"]) >= 45
            for x in lessons),
        "12_four_distinct_skills": all(set(x.get("tasks", {})) == set(SKILLS) for x in lessons),
        "13_prompts_no_word_bank": all(not any(k in t for k in ("options", "choices", "word_bank"))
                                       for t in all_tasks),
        "14_answer_keys_only_for_narrow_tasks": all(
            all(isinstance(x["tasks"][k].get("accepted"), list)
                and x["tasks"][k]["model"] in x["tasks"][k]["accepted"]
                and x["tasks"][k]["prompt"].strip()
                for k in ("meaning", "writing"))
            and all("accepted" not in x["tasks"][k]
                    and x["tasks"][k]["prompt"].strip()
                    and x["tasks"][k]["model"].strip()
                    for k in ("transfer", "explain"))
            for x in lessons),
        "15_bounds_and_no_model_in_prompt": all(
            all(isinstance(t.get("prompt"), str) and isinstance(t.get("model"), str)
                and 12 <= len(t["prompt"]) <= 600 and 1 <= len(t["model"]) <= 400
                and t["prompt"].strip().casefold() != t["model"].strip().casefold()
                for t in x["tasks"].values())
            and "работает такая схема" not in x["tasks"]["explain"]["prompt"].lower()
            and x["pattern"].casefold() not in x["tasks"]["explain"]["prompt"].casefold()
            for x in lessons),
    }


def scaffold_bank():
    """Server-side editorial mini-lessons and alternate real-life transfer tasks."""
    path = settings.CONTENT_DIR / "manifests" / "a1_scaffold_transfer.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("lessons", [])
    base_document = json.loads(
        (settings.CONTENT_DIR / "manifests" / "a1_understanding_checks.json").read_text(encoding="utf-8")
    )
    understanding_tasks = {
        entry["slug"]: entry["tasks"]["transfer"] for entry in base_document["lessons"]
    }
    if data.get("version") != 1 or data.get("level") != "A1":
        raise ValueError("Invalid A1 scaffold manifest")
    if len(rows) != 28 or set(x.get("slug") for x in rows) != PILOT_SLUGS:
        raise ValueError("A1 scaffold must cover every lesson exactly once")
    if len(set(x["slug"] for x in rows)) != 28:
        raise ValueError("Duplicate A1 scaffold")
    for item in rows:
        steps = item.get("steps", [])
        tasks = item.get("transfer_variants", [])
        if len(steps) != 3 or any(
            not (isinstance(step.get("example_en"), str)
                 and len(step["example_en"].strip()) >= 3
                 and isinstance(step.get("example_ru"), str)
                 and len(step["example_ru"].strip()) >= 3
                 and isinstance(step.get("why_ru"), str)
                 and len(step["why_ru"].strip()) >= 25)
            for step in steps
        ):
            raise ValueError("Incomplete beginner explanation: " + item["slug"])
        if len({step["example_en"].strip().casefold() for step in steps}) != 3:
            raise ValueError("Duplicate examples: " + item["slug"])
        if not isinstance(tasks, list) or len(tasks) != 2:
            raise ValueError("Each lesson needs two extra transfer tasks: " + item["slug"])
        baseline = understanding_tasks.get(item["slug"], {})
        seen_prompts = {baseline.get("prompt", "").strip().casefold()}
        seen_models = {baseline.get("model", "").strip().casefold()}
        for task in tasks:
            if not isinstance(task, dict) or set(task) != {"prompt", "model"}:
                raise ValueError("Transfer challenge contains answer keys or unsupported fields")
            prompt, model = task["prompt"], task["model"]
            if (not isinstance(prompt, str) or not 24 <= len(prompt.strip()) <= 600
                    or not isinstance(model, str) or not 12 <= len(model.strip()) <= 400
                    or prompt.strip().casefold() == model.strip().casefold()):
                raise ValueError("Invalid free transfer text: " + item["slug"])
            if prompt.strip().casefold() in seen_prompts:
                raise ValueError("Repeated transfer prompt: " + item["slug"])
            seen_prompts.add(prompt.strip().casefold())
            # Different prompts can sometimes share an A1 answer, but they must
            # test different communicative acts; avoid rote repeating the model.
            if model.strip().casefold() in seen_models:
                raise ValueError("Repeated transfer sample: " + item["slug"])
            seen_models.add(model.strip().casefold())
    return {x["slug"]: x for x in rows}


@lru_cache(maxsize=1)
def understanding_bank():
    path = settings.CONTENT_DIR / "manifests" / "a1_understanding_checks.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    gates = quality_gates(data)
    failures = [name for name, passed in gates.items() if not passed]
    if failures:
        raise ValueError("A1 clarity / independent assessment checks failed: " + ", ".join(failures))
    extras = scaffold_bank()
    compiled = {}
    for row in data["lessons"]:
        extra = extras[row["slug"]]
        compiled[row["slug"]] = {
            **row,
            "steps": extra["steps"],
            "transfer_variants": extra["transfer_variants"],
        }
    return compiled


def get_guide(slug):
    return understanding_bank().get(slug)


def model_agreement(task, submitted):
    """Only proof of a known phrase match, NEVER proof that other phrasings are wrong."""
    from apps.drills.models import Exercise
    answer = Exercise.normalize(submitted)
    return bool(answer and answer in {
        Exercise.normalize(s) for s in task.get("accepted", [])
    })
