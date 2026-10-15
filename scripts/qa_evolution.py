"""Reproducible, progressively stronger input probes and a CI quality gate."""
from __future__ import annotations

import argparse
import html
import json
import os
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789<&>\"'абвгдеёжзийклмнопрстуфхцчшщыэюя"


def fuzz_budget(run_number: int, *, deep: bool = False) -> tuple[int, int]:
    """Increase depth with CI runs; cap it to bound time and resource usage."""
    run_number = max(0, run_number)
    rounds = min(1200, 64 + 12 * run_number)
    length = min(120, 12 + run_number // 2)
    return (min(6000, rounds * 5) if deep else rounds, length)


def run_fuzz(seed: int, run_number: int, deep: bool = False) -> None:
    # Direct execution (python scripts/qa_evolution.py) must resolve Django project imports.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
    import django

    django.setup()
    from apps.drills.models import Exercise
    from apps.lexicon.phonetics import _CONSONANTS, _VOWELS, to_plain, unknown_symbols
    from apps.taxonomy.markup import find_issues, render_inline, strip_markup

    rng = random.Random(seed)
    rounds, max_len = fuzz_budget(run_number, deep=deep)
    ipa_tokens = [*_CONSONANTS, *_VOWELS]
    for index in range(rounds):
        case = ""
        stage = ""
        try:
            stage = "linguistic markup round-trip and HTML escaping"
            case = "".join(rng.choices(ALPHABET, k=rng.randint(1, max_len)))
            annotated = f"[S1]{case}[/]"
            assert find_issues(annotated) == []
            assert strip_markup(annotated) == case
            rendered = render_inline(annotated)
            assert html.escape(case, quote=True) in rendered
            assert "<script>" not in rendered

            stage = "answer normalization is idempotent"
            normalized = Exercise.normalize(case)
            assert Exercise.normalize(normalized) == normalized

            stage = "alternative answers remain valid"
            answer = "".join(rng.choices("abcdefghijklmno", k=rng.randint(1, 24)))
            exercise = Exercise(answer="unused", accepted=[answer])
            assert exercise.is_correct("  " + answer.upper() + ". ")

            stage = "known IPA tokens produce a transcription"
            ipa = "/" + " ".join(rng.choices(ipa_tokens, k=rng.randint(1, 12))) + "/"
            assert unknown_symbols(ipa) == set()
            assert to_plain(ipa)
        except Exception:
            print(f"Counterexample: seed={seed} index={index} stage={stage} input={case!r}", file=sys.stderr)
            raise
    print(f"QA fuzz passed: cases={rounds} max_length={max_len} seed={seed} tier={'deep' if deep else 'regular'}")


def parse_test_count(junit_xml: Path) -> int:
    root = ET.parse(junit_xml).getroot()
    return sum(1 for node in root.iter("testcase"))


def make_quality_report(coverage: dict, test_count: int, baseline: dict) -> tuple[str, list[str]]:
    covered = float(coverage["totals"]["percent_covered"])
    floor = float(baseline["minimum_coverage_percent"])
    min_tests = int(baseline["minimum_test_cases"])
    failures: list[str] = []
    if covered + 1e-9 < floor:
        failures.append(f"Coverage below {floor:.2f}%: got {covered:.2f}%")
    if test_count < min_tests:
        failures.append(f"Tests below {min_tests}: got {test_count}")

    needs_tests = []
    for path, item in coverage.get("files", {}).items():
        summary = item.get("summary", {})
        if int(summary.get("num_statements", 0)) < 12:
            continue
        percent = float(summary.get("percent_covered", 100))
        missing = len(item.get("missing_lines", []))
        needs_tests.append((percent, -missing, path, missing))
    needs_tests.sort()
    lines = [
        "# English-Encyclopedia: quality evolution",
        "",
        f"- **Branch-aware coverage:** {covered:.2f}% (floor {floor:.2f}%)",
        f"- **Test cases:** {test_count} (floor {min_tests})",
        "- **Fuzz:** increasingly many randomized inputs, seed reproducible from logs",
        "- **Ratchet:** raise coverage/test floors only after tested, reviewed changes",
        "",
        "## Modules to cover next",
        "",
        "| Module | Coverage | Missing lines |",
        "|---|---:|---:|",
    ]
    for percent, _, path, missing in needs_tests[:12]:
        lines.append(f"| {path} | {percent:.1f}% | {missing} |")
    if not needs_tests:
        lines.append("| (none) | — | — |")
    lines += ["", "## Quality gate", ""]
    lines += [f"- FAILED: {s}" for s in failures] if failures else ["- PASSED: coverage and test-case floors"]
    lines += ["", "Reports do not modify application code or approve PRs.", ""]
    return "\n".join(lines), failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fuzz = sub.add_parser("fuzz")
    fuzz.add_argument("--run-number", type=int, default=0)
    fuzz.add_argument("--seed", type=int, default=20261015)
    fuzz.add_argument("--deep", action="store_true")
    report = sub.add_parser("report")
    report.add_argument("--coverage-json", type=Path, required=True)
    report.add_argument("--junit-xml", type=Path, required=True)
    report.add_argument("--baseline", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "fuzz":
        run_fuzz(args.seed, args.run_number, args.deep)
        return 0

    coverage = json.loads(args.coverage_json.read_text(encoding="utf-8"))
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    count = parse_test_count(args.junit_xml)
    markdown, failures = make_quality_report(coverage, count, baseline)
    args.output.write_text(markdown, encoding="utf-8")
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(markdown)
    print(markdown)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
