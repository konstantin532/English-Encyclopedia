from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parent.parent


class SituationWeekDocumentationTests(SimpleTestCase):
    def test_author_and_launch_instructions_cover_weeks(self):
        expected = {
            "README.md": ("seed_weeks", "spoken", "ee-speech-mode", "generate_audio.bat", "--all --engine test"),
            "CLAUDE.md": ("seed_weeks", "spoken", "gonna", "audit_course"),
            "docs/CONTEXT.md": ("Сцена недели", "Сфера", "Скороговорка", "Цель недели"),
        }
        for path, terms in expected.items():
            text = (ROOT / path).read_text(encoding="utf-8")
            for term in terms:
                with self.subTest(path=path, term=term):
                    self.assertIn(term, text)
