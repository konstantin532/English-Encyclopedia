"""Второй педагогический проход A1: правила перехода к практике, 1–26.

Тесты защищают структурные и смысловые договорённости. Они не доказывают,
что урок понятен новичку без наблюдения за реальными учениками.
"""
from pathlib import Path
import re

import yaml
from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[1] / "content" / "seed_lessons"


def course_lessons():
    paths = sorted(ROOT.glob("a1_w*_l*.yaml"))
    lessons = {}
    for path in paths:
        lesson = yaml.safe_load(path.read_text(encoding="utf-8"))
        order = lesson["order"]
        if 1 <= order <= 26:
            assert order not in lessons, f"Duplicate lesson order: {order}"
            lessons[order] = lesson
    return lessons


class A1SecondPassTests(SimpleTestCase):
    def test_all_26_lessons_have_one_contextual_reasoning_bridge(self):
        lessons = course_lessons()
        self.assertEqual(set(lessons), set(range(1, 27)))
        for order, lesson in lessons.items():
            with self.subTest(lesson=order):
                self.assertEqual(lesson["level"], "A1")
                self.assertEqual(lesson["week"], (order + 1) // 2)
                self.assertEqual([layer["number"] for layer in lesson["layers"]],
                                 list(range(1, 8)))
                # Короткий разбор стоит непосредственно перед практикой.
                bridge = lesson["layers"][6]["body"]
                self.assertEqual(bridge.count("**Проверка маленького шага:**"), 1)
                self.assertIn("**", bridge)
                self.assertGreaterEqual(len(bridge.split()), 45)

    def test_marked_examples_remain_balanced(self):
        for order, lesson in course_lessons().items():
            with self.subTest(lesson=order):
                body = "\n".join(layer["body"] for layer in lesson["layers"])
                self.assertEqual(len(re.findall(r"\[[A-Z]\d+\]", body)),
                                 body.count("[/]"))

    def test_important_second_pass_repairs(self):
        lessons = course_lessons()
        self.assertNotIn("название почти никогда не стоит в одиночку",
                         lessons[1]["summary"])
        self.assertIn("двух примерах", lessons[2]["layers"][6]["body"])

        book = lessons[3]["exercises"][0]
        self.assertIn("неизвестную ему", book["prompt_ru"])

        pricing = next(e for e in lessons[10]["exercises"] if e["order"] == 5)
        self.assertIn("для вас", pricing["prompt_ru"])
        self.assertEqual(pricing["answer"], "That is expensive!")

        letters = next(e for e in lessons[18]["exercises"] if e["order"] == 2)
        self.assertNotIn("Вы слышите", letters["prompt_ru"])
        self.assertIn("/iː/", letters["prompt_ru"])

        address = next(e for e in lessons[24]["exercises"] if e["order"] == 3)
        self.assertIn("вслух", address["prompt_ru"])
        self.assertEqual(address["answer"], "five Park Street")
        self.assertIn("5 Park Street", lessons[24]["layers"][6]["body"])

    def test_reasons_distinguish_common_lookalikes(self):
        expected = {
            4: ("I have a phone", "Can I have a phone?"),
            5: ("I like coffee", "I'd like a coffee"),
            9: ("I have a book", "There is a book"),
            11: ("Do you get up at six?", "What time do you get up?"),
            13: ("Tom works", "Does Tom work?"),
            16: ("Turn right", "on the right"),
            17: ("Who works here?", "Where does Tom work?"),
            19: ("I always read", "I am always busy"),
            21: ("My foot hurts", "My feet hurt"),
            23: ("She isn't at home", "She doesn't work at home"),
            26: ("Because I like music", "Because of the music"),
        }
        for number, examples in expected.items():
            layer = course_lessons()[number]["layers"][6]["body"]
            for example in examples:
                with self.subTest(lesson=number, example=example):
                    self.assertIn(example, layer)
