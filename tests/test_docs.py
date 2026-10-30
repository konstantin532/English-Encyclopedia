from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parent.parent


class SituationWeekDocumentationTests(SimpleTestCase):
    def test_author_and_launch_instructions_cover_weeks(self):
        expected = {
            "README.md": ("seed_weeks", "spoken", "ee-speech-mode", "generate_audio.bat", "--all --engine test"),
            "AGENTS.md": ("spoken", "gonna", "audit_course"),
            ".agents/skills/course-content/SKILL.md": ("seed_weeks", "--all --engine test"),
            "docs/CONTEXT.md": ("Сцена недели", "Сфера", "Скороговорка", "Цель недели"),
        }
        for path, terms in expected.items():
            text = (ROOT / path).read_text(encoding="utf-8")
            for term in terms:
                with self.subTest(path=path, term=term):
                    self.assertIn(term, text)

    def test_claude_md_imports_agents_md(self):
        # Claude Code не читает AGENTS.md, если рядом есть CLAUDE.md, — только через импорт.
        # Тест живёт здесь, потому что правка одного CLAUDE.md запускает в CI только тесты документации.
        lines = (ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
        first = next(line.strip() for line in lines if line.strip())
        self.assertEqual(first, "@AGENTS.md")
