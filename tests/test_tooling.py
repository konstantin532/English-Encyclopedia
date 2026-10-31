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
MIXED_EOL_LEGACY_MAX = 6


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

    def test_mixed_line_ending_legacy_list_only_shrinks(self):
        import yaml

        config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
        hooks = [hook for repo in config["repos"] for hook in repo["hooks"]]
        exclude = next(hook for hook in hooks if hook["id"] == "mixed-line-ending")["exclude"]
        legacy = [path.replace("\\.", ".") for path in exclude.removeprefix("^(").removesuffix(")$").split("|")]
        self.assertLessEqual(len(legacy), MIXED_EOL_LEGACY_MAX)
        self.assertEqual([path for path in legacy if not (ROOT / path).is_file()], [])


class RepositoryProcessTests(SimpleTestCase):
    """Шаблоны задач, метки, владельцы кода и среда разработки согласованы между собой."""

    def labels(self) -> set[str]:
        import json

        return {label["name"] for label in json.loads((ROOT / ".github" / "labels.json").read_text(encoding="utf-8"))}

    def test_issue_templates_use_known_labels(self):
        import yaml

        templates = sorted((ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml"))
        forms = [t for t in templates if t.name != "config.yml"]
        self.assertGreaterEqual(len(forms), 3)
        for path in forms:
            with self.subTest(template=path.name):
                form = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertTrue(form["name"] and form["description"] and form["body"])
                self.assertLessEqual(set(form.get("labels", [])), self.labels())

    def test_dependabot_uses_known_labels(self):
        import yaml

        config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
        ecosystems = {u["package-ecosystem"] for u in config["updates"]}
        self.assertEqual(ecosystems, {"uv", "npm", "github-actions"})
        for update in config["updates"]:
            self.assertLessEqual(set(update.get("labels", [])), self.labels())

    def test_codeowners_names_the_author(self):
        self.assertIn("* @konstantin532", (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8"))

    def test_devcontainer_matches_project_versions(self):
        import json

        config = json.loads((ROOT / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8"))
        compose = (ROOT / ".devcontainer" / config["dockerComposeFile"]).read_text(encoding="utf-8")
        python = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
        self.assertIn(f"devcontainers/python:{python}", compose)
        self.assertIn("postgres:16", compose)
        self.assertIn("codex_cloud_setup.sh", config["postCreateCommand"])

    def test_droid_review_is_pinned_and_skips_without_key(self):
        import yaml

        path = ROOT / ".github" / "workflows" / "droid-review.yml"
        workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        job = workflow["jobs"]["review"]
        self.assertIn("draft == false", job["if"])
        action = next(step for step in job["steps"] if step.get("uses", "").startswith("Factory-AI/droid-action@"))
        self.assertRegex(action["uses"], r"@[0-9a-f]{40}$")
        self.assertEqual(action["with"]["automatic_review"], "true")
        self.assertEqual(action["if"], "steps.check.outputs.configured == 'true'")
        checkout = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))
        self.assertEqual(checkout["with"]["persist-credentials"], "false")
