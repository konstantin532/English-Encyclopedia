"""Шесть симулированных учеников: без сети, денег и реальных данных."""
import json
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from scripts import virtual_a1_students as bots


class VirtualStudentTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lessons = bots.load_lessons(bots.ROOT, 1, 26)
        cls.active = bots.load_active(bots.ROOT)

    def test_six_distinct_virtual_personas_and_all_a1_lessons(self):
        self.assertEqual(len(bots.PERSONAS), 6)
        self.assertEqual(len({item[0] for item in bots.PERSONAS}), 6)
        self.assertEqual(set(self.lessons), set(range(1, 27)))
        self.assertTrue(all(n in self.active for n in range(1, 27)))

    def test_rules_mode_has_no_llm_traffic_and_is_labeled_as_simulation(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            with patch.object(bots, "call_ollama", side_effect=AssertionError("network")):
                report = bots.run(bots.ROOT, mode="rules", report_dir=Path(directory))
            self.assertEqual(report["checks"], 26 * 6)
            self.assertEqual(report["calls"], 0)
            self.assertEqual(report["attempts"], [])
            self.assertFalse(report["partial"])
            self.assertTrue(report["findings"])
            self.assertIn("не испытывают", report["warning"])
            written = json.loads((Path(directory) / "virtual-students.json").read_text("utf-8"))
            self.assertEqual(written["calls"], 0)
            md = (Path(directory) / "virtual-students.md").read_text("utf-8")
            self.assertIn("СИМУЛЯЦИЯ", md)
            self.assertIn("эвристики не решают задания", md)

    def test_blind_packet_never_leaks_canonical_answers_or_hints(self):
        lesson = self.lessons[14]
        packet = bots.blind_packet(lesson, self.active[14], "Предыдущие навыки")
        tasks = packet["tasks"]
        self.assertEqual(len(tasks), len(lesson["exercises"]))
        for task in tasks:
            for banned in ("answer", "accepted", "hint_ru", "explanation_ru"):
                self.assertNotIn(banned, task)
        self.assertNotIn("answer", packet)
        self.assertIn("layers", packet)

    def test_validate_real_quote_and_dismiss_hallucinated_source(self):
        lesson = self.lessons[14]
        evidence = bots.evidence_for(lesson, self.active[14])
        answer = lesson["exercises"][0]["answer"]
        obj = {
            "questions": [
                {"source": "layer:1", "quote": "НИЧЕГО ТАКОГО В УРОКЕ НЕТ",
                 "question": "Что значит эта фраза?", "category": "other"},
                {"source": "layer:3", "quote": "I am a doctor.",
                 "question": "Почему здесь am?", "category": "terminology"},
            ],
            "attempts": [{"exercise": 1, "response": answer}],
            "learning_summary": "Частично понятен be",
        }
        issues, attempts, memory = bots.parse_result(bots.PERSONAS[0], 14, obj, evidence, lesson)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["source"], "layer:3")
        self.assertEqual(len(attempts), 1)
        self.assertTrue(attempts[0]["matches_key"])
        self.assertEqual(memory, "Частично понятен be")

    def test_open_answer_is_not_marked_as_semantically_wrong(self):
        self.assertEqual(bots.norm(" I'm a doctor. "), bots.norm("I'm a doctor"))
        lesson = self.lessons[14]
        obj = {"questions": [], "attempts": [{"exercise": 4, "response": "I work in a hospital."}]}
        issues, attempts, _ = bots.parse_result(
            bots.PERSONAS[4], 14, obj, bots.evidence_for(lesson, self.active[14]), lesson)
        self.assertFalse(issues)
        self.assertFalse(attempts[0]["matches_key"])
        self.assertIn("проверки человеком", attempts[0]["note"].lower())

    def test_local_ollama_budget_and_response_can_be_mocked(self):
        mock_answer = {"questions": [], "attempts": [], "learning_summary": "Есть сомнения"}
        with patch.object(bots, "call_ollama", return_value=mock_answer) as ai:
            report = bots.run(bots.ROOT, first=1, last=2, mode="ollama", max_calls=2)
        self.assertEqual(report["calls"], 2)
        self.assertEqual(report["checks"], 2)
        self.assertTrue(report["partial"])
        self.assertEqual(ai.call_count, 2)

    def test_local_only_endpoint_and_plain_markup(self):
        self.assertEqual(bots.URL, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(bots.plain("[T8]I[/] [D1]am[/]"), "I am")
