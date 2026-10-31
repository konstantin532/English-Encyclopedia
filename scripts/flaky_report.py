#!/usr/bin/env python3
"""Нестабильные тесты: сравнивает отчёты JUnit нескольких прогонов одного кода.

    python scripts/flaky_report.py run-1/junit.xml run-2/junit.xml run-3/junit.xml --output flaky.md

Тест, который в одних прогонах прошёл, а в других упал, — нестабильный (flaky): он зависит от
порядка, времени или общего состояния. Тест, упавший во всех прогонах, — обычная поломка.
Код выхода 1, если нашлись нестабильные тесты.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def outcomes(path: Path) -> dict[str, bool]:
    """Имя теста → прошёл ли он. Пропущенные тесты не учитываются."""
    result = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        if case.find("skipped") is not None:
            continue
        name = f"{case.get('classname', '')}::{case.get('name', '')}"
        result[name] = case.find("failure") is None and case.find("error") is None
    return result


def classify(runs: list[dict[str, bool]]) -> tuple[list[str], list[str]]:
    seen: dict[str, list[bool]] = defaultdict(list)
    for run in runs:
        for name, passed in run.items():
            seen[name].append(passed)
    flaky = sorted(name for name, results in seen.items() if any(results) and not all(results))
    broken = sorted(name for name, results in seen.items() if not any(results))
    return flaky, broken


def render(flaky: list[str], broken: list[str], runs: int) -> str:
    lines = [f"# Нестабильные тесты ({runs} прогонов в случайном порядке)", ""]
    if not flaky and not broken:
        lines.append("Все тесты дали одинаковый результат во всех прогонах.")
    if flaky:
        lines += ["## Нестабильные (то проходят, то падают)", "", *[f"- `{name}`" for name in flaky], ""]
    if broken:
        lines += ["## Падают во всех прогонах", "", *[f"- `{name}`" for name in broken], ""]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    runs = [outcomes(path) for path in args.reports]
    flaky, broken = classify(runs)
    report = render(flaky, broken, len(runs))
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    sys.stdout.write(report)
    return 1 if flaky else 0


if __name__ == "__main__":
    raise SystemExit(main())
