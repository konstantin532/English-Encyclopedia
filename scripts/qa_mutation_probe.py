"""Mutation probes: break a throwaway copy to see whether real tests detect it."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MUTATIONS = (
    ("Curly apostrophes", '.replace("’", "\'")', '.replace("’", "’")', "test_normalize_curly_apostrophe"),
    ("Trailing punctuation", '.strip(" .!?")', '.strip(" ")', "test_normalize_trailing_punctuation"),
    ("Comma separation", '.replace(",", " ")', '.replace(",", ",")', "test_normalize_comma_as_separator"),
    ("Accepted alternatives", "[self.answer, *self.accepted]", "[self.answer]", "test_exercise_accepts_alternative_answers"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path("mutation-report.md"))
    args = parser.parse_args()
    project = Path(__file__).resolve().parent.parent
    outcomes = []

    with tempfile.TemporaryDirectory(prefix="ee-mutation-") as tmp:
        sandbox = Path(tmp) / "checkout"
        shutil.copytree(
            project, sandbox,
            ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", ".coverage", "staticfiles", "models"),
        )
        target = sandbox / "apps/drills/models.py"
        original = target.read_text(encoding="utf-8")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for label, old, new, test_name in MUTATIONS:
            if original.count(old) != 1:
                outcomes.append((label, "ERROR: mutation anchor changed"))
                continue
            target.write_text(original.replace(old, new, 1), encoding="utf-8")
            cmd = [
                sys.executable, "-m", "pytest", "-q", "--disable-warnings",
                f"tests/test_qa_evolution.py::ProgressiveQualityTests::{test_name}",
            ]
            try:
                result = subprocess.run(cmd, cwd=sandbox, env=env, text=True, capture_output=True, timeout=120)
            except subprocess.TimeoutExpired:
                outcomes.append((label, "ERROR: probe timed out"))
                continue
            finally:
                target.write_text(original, encoding="utf-8")

            output = result.stdout + result.stderr
            if result.returncode != 0 and "1 failed" in output and "AssertionError" in output:
                outcomes.append((label, "KILLED: detected by test"))
            elif result.returncode == 0:
                outcomes.append((label, "SURVIVED: test needs strengthening"))
            else:
                outcomes.append((label, "ERROR: pytest failed unexpectedly"))
                print(f"Probe error ({label}):\n{output[-2000:]}", file=sys.stderr)

    detected = sum(status.startswith("KILLED") for _, status in outcomes)
    lines = [
        "# English-Encyclopedia mutation probes", "",
        f"**Detected {detected}/{len(MUTATIONS)} deliberately introduced bugs.**", "",
        "| Mutated behavior | Result |", "|---|---|",
        *(f"| {label} | {status} |" for label, status in outcomes),
        "", "This is a small smoke test, not a full mutation score. No project files were changed.", "",
    ]
    markdown = "\n".join(lines)
    args.report.write_text(markdown, encoding="utf-8")
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(markdown)
    print(markdown)
    return 0 if detected == len(MUTATIONS) else 1


if __name__ == "__main__":
    sys.exit(main())
