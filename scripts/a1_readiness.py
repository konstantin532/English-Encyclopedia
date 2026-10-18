"""A1 foundation report: content inventory is not evidence of learner proficiency.

Usage:
    uv run python scripts/a1_readiness.py
    uv run python scripts/a1_readiness.py --json
    uv run python scripts/a1_readiness.py --strict

--strict fails for missing or malformed *structural* materials only.
It does not certify CEFR, spoken English, accessibility or learning outcomes.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"weeks": 14, "lessons": 28, "units": 500, "stories": 5,
            "poems": 7, "twisters": 14, "missions": 168, "twists": 56}
SCENARIOS = sorted((ROOT / "content" / "active_a1").glob("scenarios_*.json"))


def read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def a1_media_files(folder, prefix, count):
    accepted = {f"{prefix}{number:02d}_" for number in range(1, count + 1)}
    return sorted(p for p in folder.glob(f"{prefix}*.yaml") if p.name[:4] in accepted)


def audit(root=ROOT):
    """Check the real YAML/JSON inventory; never infer genuine learning from it."""
    folder = root / "content"
    weeks = [read_yaml(p) for p in sorted((folder / "seed_weeks").glob("a1_w*.yaml"))]
    lessons = [read_yaml(p) for p in sorted((folder / "seed_lessons").glob("a1_w*_l*.yaml"))]
    lexical = [read_yaml(p) for p in sorted((folder / "seed_lexicon").glob("*.yaml"))]
    units = [unit for pack in lexical if pack.get("level") == "A1"
             for unit in pack.get("units", [])]
    # Do not mistake future A1+ stories and poems for A1 inventory drift.
    story_files = a1_media_files(folder / "seed_stories", "s", 5)
    poem_files = a1_media_files(folder / "seed_poems", "p", 7)
    stories = [read_yaml(p) for p in story_files]
    poems = [read_yaml(p) for p in poem_files]
    scenes = [row for p in sorted((folder / "active_a1").glob("scenarios_*.json"))
              for row in json.loads(p.read_text(encoding="utf-8"))]
    week_numbers = [w.get("week") for w in weeks]
    lesson_orders = [l.get("order") for l in lessons]
    unit_ids = [u.get("uid") for u in units]
    week_load = Counter(int(pack["week"]) for pack in lexical if pack.get("level") == "A1"
                        for _ in pack.get("units", []) if pack.get("week") is not None)

    checks = {
        "weeks": len(weeks) == EXPECTED["weeks"] and sorted(week_numbers) == list(range(1, 15)),
        "lessons": len(lessons) == EXPECTED["lessons"]
                   and sorted(lesson_orders) == list(range(1, 29))
                   and all([layer.get("number") for layer in l.get("layers", [])] == list(range(1, 8))
                           and l.get("level") == "A1" for l in lessons),
        "units": len(units) == EXPECTED["units"] and len(set(unit_ids)) == EXPECTED["units"]
                 and None not in unit_ids,
        "weekly_load": set(week_load) == set(range(1, 15))
                       and all(30 <= week_load[n] <= 39 for n in range(1, 15)),
        "stories": len(stories) == EXPECTED["stories"]
                   and sorted(s.get("number") for s in stories) == list(range(1, 6)),
        "poems": len(poems) == EXPECTED["poems"]
                 and sorted(p.get("number") for p in poems) == list(range(1, 8)),
        "twisters": sum(bool(w.get("twister")) for w in weeks) == EXPECTED["twisters"],
        "missions": sorted(s.get("n") for s in scenes) == list(range(1, 29))
                    and sum(len(s.get("missions", [])) for s in scenes) == EXPECTED["missions"]
                    and all([m.get("id") for m in s.get("missions", [])] == list(range(1, 7))
                            for s in scenes),
        "twists": sum(len(s.get("twists", [])) for s in scenes) == EXPECTED["twists"],
    }
    reviewed = sum(u.get("verification_status") == "verified" and
                   u.get("cefr") not in (None, "unverified") for u in units)
    result = {
        "level": "A1",
        "counts": {
            "weeks": len(weeks), "lessons": len(lessons), "units": len(units),
            "stories": len(stories), "poems": len(poems),
            "twisters": sum(bool(w.get("twister")) for w in weeks),
            "missions": sum(len(s.get("missions", [])) for s in scenes),
            "twists": sum(len(s.get("twists", [])) for s in scenes),
            "cefr_verified_units": reviewed,
            "cefr_not_fully_verified_units": len(units) - reviewed,
        },
        "weekly_units": {str(i): week_load[i] for i in range(1, 15)},
        "checks": checks,
        "structural_pass": all(checks.values()),
        "independent_evidence": {
            "american_audio_human_review": "not established by this audit",
            "mobile_and_accessibility_human_review": "not established by this audit",
            "independent_spoken_and_listening_pilot": "not established by this audit",
            "delayed_learning_results": "not established by this audit",
        },
        "a1_plus_gate": "NOT CERTIFIED: content counts and automated tests do not prove CEFR A1.",
    }
    return result


def markdown(result):
    lines = [
        "# A1: проверка фундамента",
        "",
        "Этот отчёт проверяет структуру файлов, а не владение английским.",
        "",
        "## Материалы",
    ]
    for name, count in result["counts"].items():
        lines.append("- " + name + ": " + str(count))
    lines += ["", "## Автоматические проверки"]
    for name, ok in result["checks"].items():
        lines.append("- " + ("OK" if ok else "FAIL") + ": " + name)
    lines += [
        "", "## Что нельзя считать доказанным",
        "- Американское произношение: нужно экспертное прослушивание реальных файлов.",
        "- Мобильное удобство: нужны испытания на настоящих устройствах.",
        "- Умение говорить и понимать: нужен независимый пилот с людьми.",
        "- Удержание знаний: нужна отложенная проверка без подсказок.",
        "- Готовность к A1+: этот скрипт не выдаёт сертификат A1.",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Structured machine-readable report")
    parser.add_argument("--strict", action="store_true", help="Fail on structural gaps only")
    args = parser.parse_args()
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else markdown(result), end="")
    if args.strict and not result["structural_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
