"""Разбор ошибки показывается после самостоятельной попытки, не до неё."""
from pathlib import Path

import yaml
from django.test import SimpleTestCase

from apps.taxonomy.markup import render_block


LESSONS = Path(__file__).resolve().parents[1] / "content" / "seed_lessons"


class DiagnosticRevealTests(SimpleTestCase):
    def test_all_26_a1_diagnostics_have_click_to_reveal(self):
        lessons = {}
        for path in LESSONS.glob("a1_w*_l*.yaml"):
            lesson = yaml.safe_load(path.read_text(encoding="utf-8"))
            if 1 <= lesson["order"] <= 26:
                lessons[lesson["order"]] = lesson
        self.assertEqual(set(lessons), set(range(1, 27)))
        for order, lesson in lessons.items():
            with self.subTest(lesson=order):
                layer = next(x["body"] for x in lesson["layers"] if x["number"] == 4)
                html = str(render_block(layer))
                self.assertEqual(html.count('<details class="lesson-diagnostic-answer">'), 1)
                self.assertEqual(html.count("</details>"), 1)
                self.assertIn("<summary>Показать разбор после своей попытки</summary>", html)
                self.assertIn("<strong>Разбор:</strong>", html)
                self.assertLess(html.index("Диагностика понимания:"), html.index("<details"))
                self.assertLess(html.index("<summary>"), html.index("<strong>Разбор:</strong>"))
                self.assertNotIn("<details class=\"lesson-diagnostic-answer\" open", html)

    def test_american_can_cant_pronunciation_not_taught_as_an_absolute(self):
        path = LESSONS / "a1_w11_l22_cant.yaml"
        lesson = yaml.safe_load(path.read_text(encoding="utf-8"))
        notes = lesson["sound_notes"]
        self.assertEqual(len(notes), 3)
        self.assertIn("взрыва", notes[0]["note_ru"])
        self.assertIn("/kən/", notes[1]["note_ru"])
        self.assertIn("не обязательное", notes[2]["note_ru"])
        self.assertIn("AmE", lesson["contractions"][0]["note_ru"])
        self.assertNotIn("t почти не слышно", notes[0]["note_ru"])

    def test_regular_explanations_and_examples_unchanged(self):
        regular = str(render_block("Это обычный абзац.\n\n> [T8]I[/] [D1]am[/] — Я есть"))
        self.assertNotIn("<details", regular)
        self.assertIn('<div class="example annotated">', regular)
        self.assertIn('data-cat="T"', regular)

    def test_reveal_body_is_escaped_and_remains_accessible_without_js(self):
        malicious = "**Диагностика понимания:** A или B?\n\n**Разбор:** <script>alert(1)</script> и [T8]I[/]"
        html = str(render_block(malicious))
        self.assertIn("<details", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn('data-cat="T"', html)
