"""Проверка описания PR: передача работы между Codex, Claude и автором.

Описание PR — единственный канал, по которому проверяющий узнаёт, что сделано
и чем это доказано (AGENTS.md §8). Скрипт не пускает PR без обязательных
разделов, чтобы передачу нельзя было забыть.

    python scripts/check_pr_handoff.py                 # в GitHub Actions (GITHUB_EVENT_PATH)
    python scripts/check_pr_handoff.py --body FILE     # проверить текст локально

Только стандартная библиотека: проверка идёт за секунды, без установки зависимостей.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Порядок совпадает с шаблоном .github/pull_request_template.md.
SECTIONS: tuple[str, ...] = (
    "Что и зачем",
    "Как проверено",
    "Не проверено",
    "Риски",
    "Решения без автора",
    "Урок для журнала",
)

# PR, открытые раньше этой даты, жили по старым правилам: только предупреждение.
REQUIRED_FROM = "2026-10-31T00:00:00Z"

_HEADING = re.compile(r"^\s{0,3}(?:(?P<hashes>#{1,6})\s*|\*\*)(?P<title>[^*#\n]+?)(?:\*\*)?\s*:?\s*$")
_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _normalise(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().strip(":").strip()).casefold()


def find_problems(body: str) -> list[str]:
    """Список недостающих или пустых разделов; пустой список — всё на месте."""
    wanted = {_normalise(name): name for name in SECTIONS}
    found: dict[str, list[str]] = {}
    current: str | None = None
    current_level = 0  # уровень заголовка текущего раздела: число «#», 0 — жирная строка
    # Комментарии-подсказки шаблона, в том числе многострочные, содержимым не считаются.
    for line in _COMMENT.sub("", body or "").splitlines():
        match = _HEADING.match(line)
        if match:
            level = len(match.group("hashes") or "")
            key = _normalise(match.group("title"))
            section = next((k for k in wanted if key.startswith(k)), None)
            if section is not None:
                current, current_level = section, level
                found.setdefault(current, [])
                continue
            if current is not None and current_level and level > current_level:
                continue  # подзаголовок внутри раздела: раздел продолжается
            if current is not None and not level:
                found[current].append(line.strip())  # жирная строка — обычный текст раздела
                continue
            current = None  # чужой заголовок того же или более высокого уровня
            continue
        if current is not None and line.strip():
            found[current].append(line.strip())

    problems = []
    for key, name in wanted.items():
        if key not in found:
            problems.append(f"нет раздела «{name}»")
        elif not found[key]:
            problems.append(f"раздел «{name}» пустой (если нечего сказать, напиши «нет»)")
    return problems


def _pull_request_from_event() -> dict | None:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path or not Path(path).is_file():
        return None
    event = json.loads(Path(path).read_text(encoding="utf-8"))
    return event.get("pull_request")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--body", type=Path, help="файл с текстом описания PR")
    args = parser.parse_args(argv)

    if args.body:
        body, created, author = args.body.read_text(encoding="utf-8"), REQUIRED_FROM, ""
    else:
        pr = _pull_request_from_event()
        if pr is None:
            print("Не pull request — проверять нечего.")
            return 0
        body = pr.get("body") or ""
        created = pr.get("created_at") or REQUIRED_FROM
        author = ((pr.get("user") or {}).get("login") or "").lower()

    if author.startswith("dependabot"):
        print("PR от Dependabot — передача не требуется.")
        return 0

    problems = find_problems(body)
    if not problems:
        print("Описание PR: все разделы передачи на месте.")
        return 0

    message = "Описание PR не готово к передаче (AGENTS.md §8): " + "; ".join(problems) + "."
    if created < REQUIRED_FROM:
        print(f"::warning::{message} PR открыт до {REQUIRED_FROM[:10]}, поэтому только предупреждение.")
        return 0
    print(f"::error::{message} Шаблон — .github/pull_request_template.md.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
