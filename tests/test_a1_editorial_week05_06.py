"""A1 lessons 9–12: scenario clarity and accepted-answer regressions.

Regression checks protect specific examples; they do not measure learning.
"""
import json
import re
from pathlib import Path

import yaml
from django.test import SimpleTestCase, TestCase

from apps.drills.models import PracticeItem
from tests.runner import ensure_content


ROOT = Path(__file__).resolve().parents[1] / "content" / "seed_lessons"
FILES = (
    "a1_w05_l09_there_is.yaml",
    "a1_w05_l10_how_much.yaml",
    "a1_w06_l11_present_simple.yaml",
    "a1_w06_l12_time.yaml",
)


def lesson(index):
    return yaml.safe_load((ROOT / FILES[index]).read_text(encoding="utf-8"))


def layer(data, number):
    return next(item["body"] for item in data["layers"] if item["number"] == number)


class A1WeekFiveSixEditorialStaticTests(SimpleTestCase):
    def test_preserve_lesson_structure_and_pos_markers(self):
        for index, path in enumerate(FILES):
            data = lesson(index)
            with self.subTest(path=path):
                order = index + 9
                self.assertEqual(data["level"], "A1")
                self.assertEqual(data["order"], order)
                self.assertEqual(data["week"], (order + 1) // 2)
                self.assertEqual(
                    [item["number"] for item in data["layers"]],
                    list(range(1, 8)),
                )
                self.assertEqual(
                    [item["order"] for item in data["exercises"]],
                    list(range(1, 7)),
                )
                self.assertEqual(
                    [item["order"] for item in data["practice"]],
                    [1, 2, 3, 4],
                )
                body = "\n".join(item["body"] for item in data["layers"])
                self.assertEqual(
                    len(re.findall(r"\[[A-Z]\d+\]", body)), body.count("[/]")
                )

    def test_shop_has_existence_location_and_some_contrast(self):
        data = lesson(0)
        second = layer(data, 2)
        for phrase in ("Is there milk?", "The milk is there",
                       "There is milk", "There are apples",
                       "There are some apples", "six apples"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, second)
        self.assertIn("There are some apples.", data["practice"][1]["accepted"])
        self.assertIn("Apples are red.", data["practice"][3]["accepted"])
        self.assertIn("слабым гласным /ə/", data["sound_notes"][2]["note_ru"])

    def test_price_context_distinguishes_cost_and_quantity(self):
        data = lesson(1)
        second = layer(data, 2)
        for phrase in ("How much milk?", "How much is the milk?",
                       "How many apples?", "How much are the apples?"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, second)
        self.assertIn("пакет яблок", data["exercises"][3]["prompt_ru"])
        self.assertIn("общую цену", data["exercises"][3]["prompt_ru"])
        self.assertIn("How much is milk?", data["practice"][0]["accepted"])

    def test_present_simple_is_not_a_everything_now_tense(self):
        data = lesson(2)
        second = layer(data, 2)
        for phrase in ("I work here every day", "I am at home",
                       "Do you work here?", "I don't work here"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, second)
        answer = data["practice"][3]
        self.assertIn("At seven, I drink coffee.", answer["accepted"])
        self.assertIn("не переводите have здесь дословно", data["practice"][2]["explanation_ru"])

    def test_telling_time_is_different_from_schedule_and_duration(self):
        data = lesson(3)
        second = layer(data, 2)
        for phrase in ("What time is it?", "What time do you get up?",
                       "I work seven hours", "at seven", "o'clock"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, second)
        self.assertIn("I eat at twelve o'clock.", data["practice"][1]["accepted"])
        self.assertNotIn("Какое время это?", data["practice"][2]["hint_ru"])


class A1WeekFiveSixEditorialPracticeApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def check_answer(self, slug, order, answer, expected):
        item = PracticeItem.objects.get(lesson__slug=slug, order=order)
        response = self.client.post(
            f"/api/practice/{item.pk}/check/",
            json.dumps({"answer": answer}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["correct"], expected)

    def test_shop_respects_quantity_and_reference(self):
        cases = (
            ("a1-there-is-some", 2, "There are some apples.", True),
            ("a1-there-is-some", 2, "There is apples.", False),
            ("a1-there-is-some", 4, "Apples are red.", True),
            ("a1-there-is-some", 4, "Apples is red.", False),
        )
        for slug, order, text, expected in cases:
            with self.subTest(answer=text):
                self.check_answer(slug, order, text, expected)

    def test_price_accepts_generic_milk_without_article(self):
        self.check_answer("a1-how-much-prices", 1, "How much is milk?", True)
        self.check_answer("a1-how-much-prices", 1, "How many is milk?", False)

    def test_routine_accepts_time_first(self):
        self.check_answer(
            "a1-present-simple-i-you", 4,
            "At seven, I drink coffee.", True,
        )
        self.check_answer(
            "a1-present-simple-i-you", 4,
            "At seven I am drink coffee.", False,
        )

    def test_time_accepts_full_hour_for_activity(self):
        self.check_answer(
            "a1-time-at-seven", 2,
            "I eat at twelve o'clock.", True,
        )
        self.check_answer(
            "a1-time-at-seven", 2,
            "I eat in twelve o'clock.", False,
        )
