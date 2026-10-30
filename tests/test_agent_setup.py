"""Настройка ИИ-агентов: общие скиллы, ограничители и закрытые секреты.

Эти тесты не дают настройке Claude и Codex разойтись незаметно.
"""

import filecmp
import importlib.util
import json
import re
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

    def test_every_agents_skill_is_visible_to_claude(self):
        # Claude Code не читает .agents/: навык без копии в .claude/skills для него не существует.
        claude_dir = ROOT / ".claude" / "skills"
        agents_dir = ROOT / ".agents" / "skills"
        missing = sorted(
            p.name for p in agents_dir.iterdir() if p.is_dir() and not (claude_dir / p.name).is_dir()
        )
        self.assertEqual(missing, [], "Скопируй скилл в .claude/skills без изменений")

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


class InstructionFilesTests(SimpleTestCase):
    """AGENTS.md — единственный источник правил для Codex, Claude Code и бота Codex на GitHub."""

    # Codex читает не больше 32 КБ файлов правил (project_doc_max_bytes) и молча
    # отбрасывает остальное; держим запас 8 КБ.
    AGENTS_MD_MAX_BYTES = 24 * 1024

    def test_agents_md_has_code_review_rules(self):
        # Бот Codex на GitHub ищет именно такой заголовок.
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("\n## Code Review Rules\n", text)

    def test_agents_md_fits_codex_limit(self):
        size = (ROOT / "AGENTS.md").stat().st_size
        self.assertLessEqual(size, self.AGENTS_MD_MAX_BYTES, "Сократи AGENTS.md или вынеси процедуру в навык")

    def test_instruction_links_point_to_existing_files(self):
        missing = []
        for name in ("AGENTS.md", "CLAUDE.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)#\s]+)\)", text):
                if "://" not in target and not (ROOT / target).exists():
                    missing.append(f"{name}: {target}")
        self.assertEqual(missing, [])


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

    def test_codex_approvals_go_to_auto_review(self):
        # Без автора работа не встаёт на ручном подтверждении. "never" отключил бы проверку
        # совсем, поэтому политика остаётся on-request, а отвечает проверяющий агент.
        config = tomllib.loads((ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["approval_policy"], "on-request")
        self.assertEqual(config["approvals_reviewer"], "auto_review")
        self.assertEqual(config["sandbox_mode"], "workspace-write")

    def test_cloud_setup_script_matches_ci(self):
        script = (ROOT / "scripts" / "codex_cloud_setup.sh").read_text(encoding="utf-8")
        self.assertTrue(script.startswith("#!/usr/bin/env bash\n"))
        for fragment in ("set -euo pipefail", "uv sync --frozen", "pnpm@11.25.0", "pnpm install --frozen-lockfile"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, script)


def _test_names() -> set[str]:
    names = set()
    for path in (ROOT / "tests").rglob("*.py"):
        names.update(re.findall(r"^\s*def (test_\w+)\(", path.read_text(encoding="utf-8"), flags=re.M))
    return names


class LessonsLogTests(SimpleTestCase):
    """Журнал уроков: лестница закрепления из AGENTS.md §10 проверяется, а не обещается."""

    LOG = ROOT / "docs" / "agents" / "lessons.md"

    def rows(self) -> list[list[str]]:
        rows = []
        for line in self.LOG.read_text(encoding="utf-8").splitlines():
            if line.startswith("|") and not line.startswith("|---"):
                rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        return rows[1:]  # без шапки

    def test_every_entry_is_complete(self):
        rows = self.rows()
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(row=row[:2]):
                self.assertEqual(len(row), 4, "Нужно 4 столбца: дата, категория, что случилось, чем закреплено")
                self.assertRegex(row[0], r"^(до )?\d{4}-\d{2}-\d{2}$")
                self.assertRegex(row[1], r"^[a-z][a-z-]*$")
                self.assertTrue(row[2] and row[3])

    def test_repeated_mistake_is_enforced_by_a_check(self):
        tests = _test_names()
        by_category: dict[str, list[str]] = {}
        for row in self.rows():
            by_category.setdefault(row[1], []).append(row[3])
        unenforced = []
        for category, fixes in by_category.items():
            if len(fixes) < 2:
                continue
            tokens = [t for fix in fixes for t in re.findall(r"`([^`]+)`", fix)]
            checks = [t for t in tokens if t in tests or ("/" in t and (ROOT / t).is_file())]
            if not checks:
                unenforced.append(category)
        self.assertEqual(unenforced, [], "Вторая ошибка той же категории закрепляется тестом, аудитом или хуком")

    def test_named_checks_exist(self):
        tests = _test_names()
        missing = []
        for row in self.rows():
            for token in re.findall(r"`([^`]+)`", row[3]):
                if re.fullmatch(r"test_\w+", token) and token not in tests:
                    missing.append(token)
                elif "/" in token and " " not in token and not (ROOT / token).exists():
                    missing.append(token)
        self.assertEqual(missing, [])


def _frontmatter(path: Path) -> dict:
    """Поля заголовка ---…--- файла агента Claude Code (простой YAML без вложенных словарей)."""
    import yaml

    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: нет заголовка ---"
    head = text.split("---\n", 2)[1]
    return yaml.safe_load(head)


class AgentDefinitionsTests(SimpleTestCase):
    """Агенты проекта одинаковы у Codex (.codex/agents/*.toml) и Claude Code (.claude/agents/*.md)."""

    CODEX = ROOT / ".codex" / "agents"
    CLAUDE = ROOT / ".claude" / "agents"
    READ_ONLY_TOOLS = {"Read", "Grep", "Glob", "Bash"}

    def codex_agents(self) -> dict[str, dict]:
        return {p.stem: tomllib.loads(p.read_text(encoding="utf-8")) for p in sorted(self.CODEX.glob("*.toml"))}

    def claude_agents(self) -> dict[str, dict]:
        return {p.stem: _frontmatter(p) for p in sorted(self.CLAUDE.glob("*.md"))}

    def test_both_agents_have_the_same_team(self):
        codex, claude = self.codex_agents(), self.claude_agents()
        self.assertTrue(codex)
        self.assertEqual(set(codex), set(claude), "Агент должен быть и у Codex, и у Claude Code")

    def test_codex_agents_are_complete(self):
        for stem, agent in self.codex_agents().items():
            with self.subTest(agent=stem):
                self.assertEqual(agent["name"], stem)
                self.assertTrue(agent["description"].strip())
                self.assertTrue(agent["developer_instructions"].strip())
                # Песочницу и подтверждения агент наследует; в его файле им не место.
                self.assertNotIn("sandbox_mode", agent)
                self.assertNotIn("approval_policy", agent)

    def test_claude_agents_are_complete_and_read_only(self):
        skills = {p.name for p in (ROOT / ".claude" / "skills").iterdir() if p.is_dir()}
        for stem, agent in self.claude_agents().items():
            with self.subTest(agent=stem):
                self.assertEqual(agent["name"], stem)
                self.assertTrue(agent["description"].strip())
                tools = {t.strip() for t in str(agent["tools"]).split(",")}
                self.assertLessEqual(tools, self.READ_ONLY_TOOLS, "Проверяющие агенты не правят файлы")
                self.assertLessEqual(set(agent.get("skills") or []), skills)

    def test_every_agent_promises_not_to_edit(self):
        for path in [*self.CODEX.glob("*.toml"), *self.CLAUDE.glob("*.md")]:
            with self.subTest(agent=path.name):
                self.assertIn("Файлы не меняй и не коммить", path.read_text(encoding="utf-8"))


def _load_handoff():
    spec = importlib.util.spec_from_file_location("pr_handoff", ROOT / "scripts" / "check_pr_handoff.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PullRequestHandoffTests(SimpleTestCase):
    """Описание PR — канал передачи работы между Codex, Claude и автором (AGENTS.md §8)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.handoff = _load_handoff()
        cls.template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")

    def filled(self) -> str:
        return re.sub(r"<!--.*?-->", "нет", self.template)

    def test_template_has_every_section_in_order(self):
        titles = re.findall(r"^## (.+)$", self.template, flags=re.M)
        self.assertEqual(tuple(titles), self.handoff.SECTIONS)

    def test_filled_template_passes(self):
        self.assertEqual(self.handoff.find_problems(self.filled()), [])

    def test_untouched_template_fails(self):
        problems = self.handoff.find_problems(self.template)
        self.assertEqual(len(problems), len(self.handoff.SECTIONS))

    def test_missing_section_is_named(self):
        body = self.filled().replace("## Урок для журнала", "## Прочее")
        self.assertEqual(self.handoff.find_problems(body), ["нет раздела «Урок для журнала»"])

    def test_bold_headings_are_accepted(self):
        body = "\n\n".join(f"**{name}:**\nнет" for name in self.handoff.SECTIONS)
        self.assertEqual(self.handoff.find_problems(body), [])

    def test_workflow_runs_the_check_on_description_edits(self):
        workflow = (ROOT / ".github" / "workflows" / "pr-handoff.yml").read_text(encoding="utf-8")
        self.assertIn("check_pr_handoff.py", workflow)
        self.assertIn("edited", workflow)
