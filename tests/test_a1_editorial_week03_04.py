"""Targeted A1 lessons 5–8 editorial and answer-key regressions.

The API checks prove that these concrete variants are recognized, not that
all possible natural translations can be recognized or that learning improved.
"""
import json
import re
from pathlib import Path

import yaml
from django.test import SimpleTestCase, TestCase

from apps.drills.models import PracticeItem
from tests.runner import ensure_content


SEED = Path(__file__).resolve().parents[1] / "content" / "seed_lessons"
FILES = (
    "a1_w03_l05_cafe.yaml",
    "a1_w03_l06_numbers.yaml",
    "a1_w04_l07_family.yaml",
    "a1_w04_l08_possession.yaml",
)


def get_lesson(index):
    return yaml.safe_load((SEED / FILES[index]).read_text(encoding="utf-8"))


def layer(data, number):
    return next(l["body"] for l in data["layers"] if l["number"] == number)


class FirstEightEditorialStaticTests(SimpleTestCase):
    def test_keep_structure_unique_exercises_and_unchanged_markers(self):
        for index, exercise_count in enumerate((6, 4, 6, 6)):
            data = get_lesson(index)
            with self.subTest(lesson=data["slug"]):
                self.assertEqual(data["level"], "A1")
                self.assertEqual(data["order"], index + 5)
                self.assertEqual(data["week"], (index + 5 + 1) // 2)
                self.assertEqual([l["number"] for l in data["layers"]],
                                 list(range(1, 8)))
                self.assertEqual(len(data["exercises"]), exercise_count)
                self.assertEqual([e["order"] for e in data["exercises"]],
                                 list(range(1, exercise_count + 1)))
                self.assertEqual(len(data["practice"]), 4)
                body = "\n".join(l["body"] for l in data["layers"])
                self.assertEqual(len(re.findall(r"\[[A-Z]\d+\]", body)),
                                 body.count("[/]"))

    def test_cafe_explains_meaning_before_forms(self):
        second = layer(get_lesson(0), 2)
        for phrase in ("I like coffee", "I'd like a coffee",
                       "Can I have a coffee", "Do you like coffee?",
                       "Coffee or tea?", "Can you say it again"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, second)
        cafe_practice = get_lesson(0)["practice"][1]
        self.assertIn("Can I have coffee, please?", cafe_practice["accepted"])

    def test_numbers_connect_teen_to_quantity_and_plural(self):
        data = get_lesson(1)
        second = layer(data, 2)
        for phrase in ("three", "thirteen", "eleven", "twelve",
                       "two teas", "three teas", "fifteen"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, second)
        twelve = data["practice"][2]
        self.assertIn("Can I have twelve cookies, please?", twelve["accepted"])
        self.assertIn("I would like twelve cookies, please.", twelve["accepted"])

    def test_photo_link_between_identification_and_age(self):
        data = get_lesson(2)
        second = layer(data, 2)
        for phrase in ("Who is this?", "This is my brother",
                       "How old is he?", "He is ten",
                       "He has ten"):
            self.assertIn(phrase, second)
        question = next(e for e in data["exercises"] if e["uid"] == "EX-00037")
        self.assertNotIn("как старый ты есть", question["hint_ru"])
        introducing = data["practice"][1]
        self.assertIn("фотографии", introducing["prompt_ru"])
        self.assertIn("He is my brother.", introducing["accepted"])

    def test_possession_contrasts_subject_and_owner(self):
        second = layer(get_lesson(3), 2)
        for phrase in ("She is happy", "Her photo is here",
                       "Mia's photo", "he → his", "they → their"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, second)
        self.assertIn("чья", second)


class A1Week03And04AnswerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def assert_practice(self, slug, order, answer, expected):
        item = PracticeItem.objects.get(lesson__slug=slug, order=order)
        result = self.client.post(
            f"/api/practice/{item.pk}/check/",
            json.dumps({"answer": answer}),
            content_type="application/json",
        )
        self.assertEqual(result.status_code, 200)
        self.assertIs(result.json()["correct"], expected)

    def test_cafe_accepts_uncountable_coffee_request(self):
        for answer in (
            "Can I have coffee, please?",
            "I'd like coffee, please.",
        ):
            with self.subTest(answer=answer):
                self.assert_practice("a1-cafe-order", 2, answer, True)

    def test_numbers_accept_full_polite_requests_but_require_plural(self):
        for answer in (
            "Twelve cookies, please.",
            "Can I have twelve cookies, please?",
            "I'd like twelve cookies, please.",
        ):
            with self.subTest(answer=answer):
                self.assert_practice("a1-numbers-1-20", 3, answer, True)
        self.assert_practice("a1-numbers-1-20", 3,
                             "Can I have twelve cookie, please?", False)

    def test_family_introduction_allows_known_referent(self):
        for answer in (
            "This is my brother.",
            "He is my brother.",
            "That's my brother.",
        ):
            with self.subTest(answer=answer):
                self.assert_practice("a1-family-photo", 2, answer, True)
