"""Общие ограничители для ИИ-агентов (Claude Code и Codex).

Скрипт вызывается хуками агентов и читает JSON события из stdin.

    python scripts/agent_hooks/guard.py command   # перед запуском команды
    python scripts/agent_hooks/guard.py stop      # перед тем, как агент скажет «готово»

Код выхода 2 означает «запрещено»: агент получает текст из stderr и должен
исправить подход. Любая внутренняя ошибка скрипта пропускает действие (код 0),
чтобы сломанный хук не останавливал работу; защита дублируется в CI.

Хуки — страховка от случайностей, а не песочница. Настоящую изоляцию дают
режимы одобрения и песочница самих агентов.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Команды, которые агент не выполняет без прямого решения автора.
# Каждое правило: (регулярное выражение, понятное объяснение).
DANGEROUS_COMMANDS: list[tuple[str, str]] = [
    (r"\bgit\s+push\b[^\n]*(--force\b|--force-with-lease\b|\s-f\b)", "force push переписывает историю на GitHub"),
    (r"\bgit\s+push\b[^\n]*\b(origin\s+)?(HEAD:)?main(\s|$)","push в main запрещён: автор сливает PR сам"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard безвозвратно стирает незакоммиченную работу"),
    (r"\bgit\s+clean\s+-[a-z]*f", "git clean -f удаляет неотслеживаемые файлы"),
    (r"\bgit\s+branch\s+-D\b", "принудительное удаление ветки"),
    (r"\bgit\s+checkout\s+--\s+\.", "откат всех изменений в рабочей папке"),
    (r"\brm\s+-[a-z]*r[a-z]*f?\s+(/|~|\.|\*)(\s|$)", "рекурсивное удаление корня, дома или всей папки"),
    (r"\b(Remove-Item|rd|rmdir)\b[^\n]*(-Recurse|/s)\b", "рекурсивное удаление папки"),
    (r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", "удаление таблицы или базы"),
    (r"\bTRUNCATE\s+TABLE\b", "очистка таблицы"),
    (r"\bmanage\.py\s+flush\b", "manage.py flush стирает все данные базы"),
    (r"\bmanage\.py\s+migrate\b[^\n]*\bzero\b", "откат всех миграций приложения"),
    (r"\bdb\.sqlite3\b[^\n]*(>|rm\b|del\b|Remove-Item)", "перезапись или удаление локальной базы"),
]

# Файлы с секретами: агенту не нужно их читать или печатать.
SECRET_PATTERN = re.compile(
    r"(^|[\s'\"/\\=<])\.env(?![.\w-])"  # .env, но не .env.example
)
SECRET_READERS = re.compile(r"\b(cat|type|more|less|head|tail|Get-Content|gc|grep|rg|findstr|sed|awk|cp|copy|scp|curl)\b")


def _command_from_event(event: dict) -> str:
    """Достаёт текст команды из события Claude Code или Codex."""
    tool_input = event.get("tool_input") or event.get("input") or {}
    if isinstance(tool_input, str):
        return tool_input
    for key in ("command", "cmd", "script"):
        value = tool_input.get(key)
        if isinstance(value, list):
            return " ".join(str(part) for part in value)
        if isinstance(value, str):
            return value
    return ""


def check_command(command: str) -> str | None:
    """Возвращает причину запрета или None, если команда допустима."""
    for pattern, reason in DANGEROUS_COMMANDS:
        if re.search(pattern, command, flags=re.IGNORECASE):
            return reason
    if SECRET_PATTERN.search(command) and SECRET_READERS.search(command):
        return "чтение или копирование .env с секретами"
    return None


def _changed_files() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return []
    return [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]


def stop_gate(event: dict) -> str | None:
    """Быстрые проверки перед словом «готово». Возвращает текст ошибки или None.

    Полный набор тестов здесь не запускается: он долгий и выполняется в CI.
    Шлюз ловит то, что ломает всё сразу: системные проверки Django и
    забытые миграции.
    """
    # Не зацикливаемся: если агента уже один раз вернули, второй раз пропускаем.
    if event.get("stop_hook_active"):
        return None
    changed = _changed_files()
    if not any(path.endswith(".py") for path in changed):
        return None
    python = [sys.executable, "manage.py"]
    checks = [
        (python + ["check"], "manage.py check нашёл ошибки"),
        (python + ["makemigrations", "--check", "--dry-run"], "модели изменены, а миграция не создана"),
    ]
    for cmd, message in checks:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            tail = (result.stdout + result.stderr).strip().splitlines()[-15:]
            return message + ":\n" + "\n".join(tail)
    return None


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "command"
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError):
        return 0
    try:
        if mode == "command":
            reason = check_command(_command_from_event(event))
            if reason:
                print(
                    f"Заблокировано ограничителем проекта: {reason}. "
                    "Если это действительно нужно — спроси автора в чате.",
                    file=sys.stderr,
                )
                return 2
        elif mode == "stop":
            problem = stop_gate(event)
            if problem:
                print(
                    "Рано говорить «готово». " + problem + "\nИсправь и проверь снова.",
                    file=sys.stderr,
                )
                return 2
    except Exception:  # noqa: BLE001 — сломанный хук не должен останавливать работу
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
