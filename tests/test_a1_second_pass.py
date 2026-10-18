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

    def test_future_topics_are_labeled_as_previews_not_prerequisites(self):
        lessons = course_lessons()
        previews = {
            11: ("at five", "следующий урок"),
            15: ("Can you help us?", "следующем уроке"),
            19: ("I like reading", "следующем уроке"),
            21: ("cannot / can't", "следующем уроке"),
        }
        for number, expressions in previews.items():
            opening = lessons[number]["layers"][0]["body"]
            for phrase in expressions:
                with self.subTest(lesson=number, phrase=phrase):
                    self.assertIn(phrase, opening)

    def test_free_response_options_match_the_actual_task(self):
        lessons = course_lessons()

        # «Попросите немного» требует объяснить неопределённое количество.
        bananas = next(e for e in lessons[9]["exercises"] if e["order"] == 6)
        self.assertNotIn("Yellow bananas, please.", bananas.get("accepted", []))

        # Отдельное «я играю» не обязательно означает «мне нравится».
        hobbies = next(e for e in lessons[20]["exercises"] if e["order"] == 4)
        self.assertNotIn("I play the guitar.", hobbies.get("accepted", []))
        self.assertIn("I like playing the guitar.", hobbies.get("accepted", []))

        # Не придумываем новые этапы маршрута, если известен только поворот.
        route = next(e for e in lessons[16]["exercises"] if e["order"] == 4)
        self.assertNotIn("Go straight and turn right.", route.get("accepted", []))
        self.assertEqual(route["answer"], "Turn right.")

        # Разговорный ответ может быть коротким, как сказано в условии.
        ability = next(e for e in lessons[25]["exercises"] if e["order"] == 4)
        self.assertIn("Yes, I can.", ability["accepted"])
        self.assertIn("по желанию", ability["hint_ru"])

        # Причина должна что-то объяснять, а не просто повторять вопрос.
        why = next(e for e in lessons[26]["exercises"] if e["order"] == 4)
        self.assertNotIn("Because I like English", why.get("accepted", []))
        self.assertNotIn("Because I like music.", why.get("accepted", []))

        # Американское сокращение TV пишется прописными буквами.
        television = next(e for e in lessons[11]["exercises"] if e["order"] == 6)
        self.assertFalse(any("watch tv" in candidate for candidate
                             in television.get("accepted", [])))

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
