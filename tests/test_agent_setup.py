"""Настройка ИИ-агентов: общие скиллы, ограничители и закрытые секреты.

Эти тесты не дают настройке Claude и Codex разойтись незаметно.
"""

import filecmp
import importlib.util
import json
import tomllib
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "scripts" / "agent_hooks" / "guard.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location("agent_guard", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tree_differences(left: Path, right: Path) -> list[str]:
    """Пути, которые отличаются в двух папках (без __pycache__)."""
    ignore = ["__pycache__"]
    cmp = filecmp.dircmp(left, right, ignore=ignore)
    problems = [f"{left.name}: нет в .agents — {name}" for name in cmp.left_only]
    problems += [f"{left.name}: лишнее в .agents — {name}" for name in cmp.right_only]
    _, mismatch, errors = filecmp.cmpfiles(left, right, cmp.common_files, shallow=False)
    problems += [f"{left.name}: отличается — {name}" for name in mismatch + errors]
    for sub in cmp.common_dirs:
        problems += _tree_differences(left / sub, right / sub)
    return problems


class SharedSkillsTests(SimpleTestCase):
    def test_every_claude_skill_is_visible_to_codex(self):
        claude_dir = ROOT / ".claude" / "skills"
        agents_dir = ROOT / ".agents" / "skills"
        problems = []
        for skill in sorted(p for p in claude_dir.iterdir() if p.is_dir()):
            twin = agents_dir / skill.name
            if not twin.is_dir():
                problems.append(f"{skill.name}: скилла нет в .agents/skills")
                continue
            problems += _tree_differences(skill, twin)
        self.assertEqual(problems, [], "Скопируй скилл в .agents/skills без изменений")

    def test_every_shared_skill_has_skill_md(self):
        agents_dir = ROOT / ".agents" / "skills"
        broken = [p.name for p in agents_dir.iterdir() if p.is_dir() and not (p / "SKILL.md").is_file()]
        self.assertEqual(broken, [])

    def test_design_skill_points_to_design_md(self):
        skill = (ROOT / ".agents" / "skills" / "encyclopedia-design" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("DESIGN.md", skill)
        self.assertTrue((ROOT / "DESIGN.md").is_file())


class GuardCommandTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guard = _load_guard()

    def test_blocks_destructive_commands(self):
        for command in [
            "git push --force origin chore/x",
            "git push -f",
            "git push origin main",
            "git reset --hard HEAD~3",
            "git clean -fd",
            "rm -rf /",
            "rm -rf .",
            "uv run python manage.py flush --noinput",
            "psql -c 'DROP TABLE lessons_lesson'",
            "cat .env",
            "Get-Content .env",
        ]:
            with self.subTest(command=command):
                self.assertIsNotNone(self.guard.check_command(command))

    def test_allows_normal_work(self):
        for command in [
            "git push -u origin chore/agent-guardrails",
            "git push origin fix/main-menu",
            "git status",
            "uv run python manage.py test tests --exclude-tag slow --parallel auto",
            "rm -rf node_modules/.cache",
            "cat .env.example",
            "pnpm check:css",
        ]:
            with self.subTest(command=command):
                self.assertIsNone(self.guard.check_command(command))

    def test_reads_command_from_both_agents(self):
        self.assertEqual(self.guard._command_from_event({"tool_input": {"command": "git status"}}), "git status")
        self.assertEqual(
            self.guard._command_from_event({"tool_input": {"command": ["bash", "-lc", "git status"]}}),
            "bash -lc git status",
        )

    def test_stop_gate_does_not_loop(self):
        self.assertIsNone(self.guard.stop_gate({"stop_hook_active": True}))


class AgentConfigTests(SimpleTestCase):
    def test_claude_settings_close_secrets_and_use_guard(self):
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertIn("Read(./.env)", settings["permissions"]["deny"])
        hook_commands = json.dumps(settings["hooks"])
        self.assertIn("guard.py command", hook_commands)
        self.assertIn("guard.py stop", hook_commands)

    def test_codex_config_hides_secrets_and_uses_guard(self):
        config = tomllib.loads((ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
        self.assertIn("DATABASE_URL", config["shell_environment_policy"]["exclude"])
        self.assertNotEqual(config["sandbox_mode"], "danger-full-access")
        hooks = (ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8")
        self.assertIn("guard.py command", hooks)
        self.assertIn("guard.py stop", hooks)
