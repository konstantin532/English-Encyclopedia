"""Regression checks for the scoped A1 editorial pass (lessons 1–4).

These checks verify taught contrasts and live answer keys. They do not
prove that a beginning learner has understood the explanations.
"""
import json
import re
from pathlib import Path

import yaml
from django.test import SimpleTestCase, TestCase

from apps.drills.models import PracticeItem
from tests.runner import ensure_content


LESSONS_ROOT = Path(__file__).resolve().parents[1] / "content" / "seed_lessons"
LESSON_FILES = (
    "a1_w01_l01_nouns.yaml",
    "a1_w01_l02_be.yaml",
    "a1_w02_l03_determiners.yaml",
    "a1_w02_l04_have_like_can.yaml",
)


def lesson(filename):
    return yaml.safe_load((LESSONS_ROOT / filename).read_text(encoding="utf-8"))


def layer_text(data, number):
    return next(layer["body"] for layer in data["layers"] if layer["number"] == number)


class A1FirstFourEditorialStaticTests(SimpleTestCase):
    def test_lessons_keep_ids_sequence_and_markers(self):
        for order, filename in enumerate(LESSON_FILES, start=1):
            with self.subTest(filename=filename):
                data = lesson(filename)
                self.assertEqual(data["level"], "A1")
                self.assertEqual(data["order"], order)
                self.assertEqual(data["week"], (order + 1) // 2)
                self.assertEqual(
                    [layer["number"] for layer in data["layers"]],
                    list(range(1, 8)),
                )
                body = "\n".join(layer["body"] for layer in data["layers"])
                self.assertEqual(
                    len(re.findall(r"\\[[A-Z]\\d+\\]", body)),
                    body.count("[/]"),
                )
                self.assertEqual(
                    len(data["practice"]), 4,
                    "Do not silently alter existing four translations.",
                )

    def test_noun_explanation_distinguishes_name_from_description(self):
        second = layer_text(lesson(LESSON_FILES[0]), 2)
        self.assertIn("Anna", second)
        self.assertIn("new", second)
        self.assertIn("прилагательное", second)
        self.assertIn("существительные", second)

    def test_be_explanation_requires_a_link_only_when_needed(self):
        second = layer_text(lesson(LESSON_FILES[1]), 2)
        for phrase in ("I am busy", "I like coffee", "I have a phone"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, second)
        self.assertIn("am / is / are", second)

    def test_determiners_depend_on_listener_context(self):
        data = lesson(LESSON_FILES[2])
        second = layer_text(data, 2)
        for phrase in ("a book", "the book", "this book", "my book",
                       "The table is new"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, second)
        self.assertIn("не просто «второе упоминание»", second)
        self.assertNotIn("универсальная реакция", layer_text(data, 5))

    def test_have_like_can_explains_different_questions(self):
        data = lesson(LESSON_FILES[3])
        second = layer_text(data, 2)
        for phrase in ("I have water", "I like water", "Can I have water",
                       "Do you have water", "Yes, you can"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, second)
        item = data["practice"][1]
        self.assertIn("этот дом", item["prompt_ru"])
        self.assertEqual(item["answer"], "Do you like this house?")
        self.assertIn("Do you like the house?", item["accepted"])
        self.assertNotIn("Do you like the home?", item["accepted"])


class A1FirstFourEditorialAnswerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_house_question_checks_deictic_and_known_referent(self):
        item = PracticeItem.objects.get(lesson__slug="a1-have-like-can-do", order=2)
        cases = (
            ("Do you like this house?", True),
            ("Do you like the house?", True),
            ("Do you like the home?", False),
            ("You like this house?", False),
        )
        for answer, expected in cases:
            with self.subTest(answer=answer):
                result = self.client.post(
                    f"/api/practice/{item.pk}/check/",
                    json.dumps({"answer": answer}),
                    content_type="application/json",
                )
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["correct"], expected)
