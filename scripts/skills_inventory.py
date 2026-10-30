"""Опись навыков и агентов, которые видят Codex и Claude Code.

Нужна навыку gap-audit (уровни 1 и 4): сначала посмотреть, что уже есть,
и только потом искать новое. Заодно показывает частые ловушки:

- «дубль»       — навык с тем же именем есть и в проекте, и в личной папке Codex
                  (Codex показывает оба и может взять любой);
- «нет у Claude» — навык проекта есть в .agents/skills, но нет в .claude/skills;
- «чужой стек»  — описание про React, Vue, Next, Tailwind…, а сайт на Django,
                  ванильном JS и GSAP;
- «без описания» — агент не поймёт, когда звать навык.

    python scripts/skills_inventory.py            # таблица Markdown
    python scripts/skills_inventory.py --json     # для программ
    python scripts/skills_inventory.py --home D   # другая домашняя папка (тесты)

Только чтение. Только стандартная библиотека.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FOREIGN_STACK = re.compile(r"\b(react|vue|svelte|next\.?js|nuxt|tailwind|framer)\b", re.I)
STACK_NEUTRAL = re.compile(r"\b(vanilla|plain|any framework|framework-agnostic|ванильн)", re.I)


def _skill_roots(root: Path, home: Path) -> list[tuple[str, Path]]:
    return [
        ("проект: .agents/skills", root / ".agents" / "skills"),
        ("проект: .claude/skills", root / ".claude" / "skills"),
        ("личные Codex: ~/.agents/skills", home / ".agents" / "skills"),
        ("личные Claude: ~/.claude/skills", home / ".claude" / "skills"),
    ]


def _agent_roots(root: Path, home: Path) -> list[tuple[str, Path, str]]:
    return [
        ("агенты Codex проекта: .codex/agents", root / ".codex" / "agents", "*.toml"),
        ("агенты Claude проекта: .claude/agents", root / ".claude" / "agents", "*.md"),
        ("личные агенты Codex: ~/.codex/agents", home / ".codex" / "agents", "*.toml"),
    ]


def _frontmatter(text: str) -> dict[str, str]:
    """name и description из заголовка ---…--- (однострочные и блочные значения)."""
    if not text.startswith("---"):
        return {}
    head = text.split("---", 2)[1] if text.count("---") >= 2 else ""
    fields: dict[str, str] = {}
    key = None
    for line in head.splitlines():
        match = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if match:
            key, value = match.group(1), match.group(2).strip()
            fields[key] = "" if value in {">", "|", ">-", "|-"} else value.strip("\"'")
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def inventory(root: Path = ROOT, home: Path | None = None) -> list[dict]:
    home = home or Path.home()
    items: list[dict] = []
    for where, folder in _skill_roots(root, home):
        if not folder.is_dir():
            continue
        for skill in sorted(p for p in folder.iterdir() if (p / "SKILL.md").is_file()):
            meta = _frontmatter((skill / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
            items.append({"kind": "навык", "name": meta.get("name") or skill.name,
                          "where": where, "description": meta.get("description", ""), "flags": []})
    for where, folder, pattern in _agent_roots(root, home):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob(pattern)):
            text = path.read_text(encoding="utf-8", errors="replace")
            meta = tomllib.loads(text) if path.suffix == ".toml" else _frontmatter(text)
            items.append({"kind": "агент", "name": meta.get("name") or path.stem,
                          "where": where, "description": meta.get("description", ""), "flags": []})
    _flag(items)
    return items


def _flag(items: list[dict]) -> None:
    codex_project = {i["name"] for i in items if i["where"].startswith("проект: .agents")}
    claude_project = {i["name"] for i in items if i["where"].startswith("проект: .claude")}
    for item in items:
        if item["kind"] != "навык":
            continue
        if item["where"].startswith("личные Codex") and item["name"] in codex_project:
            item["flags"].append("дубль")
        if item["where"].startswith("проект: .agents") and item["name"] not in claude_project:
            item["flags"].append("нет у Claude")
        description = item["description"]
        if not description.strip():
            item["flags"].append("без описания")
        elif FOREIGN_STACK.search(description) and not STACK_NEUTRAL.search(description):
            item["flags"].append("чужой стек")


def to_markdown(items: list[dict]) -> str:
    lines = ["| Вид | Имя | Где | Пометки | Описание |", "|---|---|---|---|---|"]
    for item in items:
        description = re.sub(r"\s+", " ", item["description"])[:110].replace("|", "/")
        lines.append(f"| {item['kind']} | {item['name']} | {item['where']} | {', '.join(item['flags'])} | {description} |")
    flagged = [i for i in items if i["flags"]]
    lines.append("")
    lines.append(f"Всего: {len(items)}; с пометками: {len(flagged)}.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Опись навыков и агентов Codex и Claude Code")
    parser.add_argument("--json", action="store_true", help="вывести JSON")
    parser.add_argument("--home", type=Path, help="домашняя папка (по умолчанию — текущего пользователя)")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # консоль Windows
    items = inventory(ROOT, args.home)
    print(json.dumps(items, ensure_ascii=False, indent=2) if args.json else to_markdown(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
