"""Линтер, форматтер и проверка типов: долг старого кода можно только сокращать."""

import re
import tomllib
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

# Сколько старых файлов было до появления проверок (2026-10-31). Числа только уменьшаются.
FORMAT_LEGACY_MAX = 282
MYPY_LEGACY_MAX = 15


def _mypy_legacy_modules() -> list[str]:
    for override in PYPROJECT["tool"]["mypy"].get("overrides", []):
        if override.get("ignore_errors"):
            return list(override["module"])
    return []


class ToolingRatchetTests(SimpleTestCase):
    def test_format_legacy_list_only_shrinks(self):
        legacy = PYPROJECT["tool"]["ruff"]["format"]["exclude"]
        self.assertLessEqual(
            len(legacy), FORMAT_LEGACY_MAX, "Новый файл должен быть отформатирован: uv run ruff format <файл>"
        )
        self.assertEqual(len(legacy), len(set(legacy)))
        missing = [path for path in legacy if not (ROOT / path).is_file()]
        self.assertEqual(missing, [], "Удалённый или переименованный файл убери из [tool.ruff.format] exclude")

    def test_mypy_legacy_list_only_shrinks(self):
        legacy = _mypy_legacy_modules()
        self.assertLessEqual(
            len(legacy), MYPY_LEGACY_MAX, "Исправь типы в новом модуле, а не добавляй его в исключения"
        )
        missing = [m for m in legacy if not (ROOT / (m.replace(".", "/") + ".py")).is_file()]
        self.assertEqual(missing, [])

    def test_lint_selects_real_error_rules(self):
        selected = set(PYPROJECT["tool"]["ruff"]["lint"]["select"])
        self.assertLessEqual({"E9", "F"}, selected, "Синтаксические ошибки и неопределённые имена проверяются всегда")

    def test_lint_workflow_runs_every_check(self):
        workflow = (ROOT / ".github" / "workflows" / "lint.yml").read_text(encoding="utf-8")
        for command in ("ruff check", "ruff format --check", "mypy", "check:css"):
            with self.subTest(command=command):
                self.assertIn(command, workflow)

    def test_pre_commit_runs_linter_and_secret_scan(self):
        config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        for hook in ("id: ruff", "id: ruff-format", "id: gitleaks", "id: mixed-line-ending"):
            with self.subTest(hook=hook):
                self.assertIn(hook, config)
        # Окончания строк только проверяются: автоматическая правка переписала бы файлы целиком.
        self.assertRegex(config, re.compile(r"id: mixed-line-ending\s+args: \[--fix=no\]"))
