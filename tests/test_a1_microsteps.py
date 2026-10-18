"""Регрессии педагогического аудита первых двух уроков A1.

Не оценивает обучение человека автоматически: защищает конкретные пояснения
и согласованность условий заданий, найденные в ходе ручного разбора.
"""
from pathlib import Path

import yaml
from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[1] / "content" / "seed_lessons"


def load_first_week(order):
    filename = {
        1: "a1_w01_l01_nouns.yaml",
        2: "a1_w01_l02_be.yaml",
    }[order]
    return yaml.safe_load((ROOT / filename).read_text(encoding="utf-8"))


def layer_text(lesson, number):
    return next(item["body"] for item in lesson["layers"] if item["number"] == number)


class A1MicrostepTests(SimpleTestCase):
    def test_existing_sequence_and_exercises_preserved(self):
        for order, exercise_count in [(1, 4), (2, 5)]:
            with self.subTest(lesson=order):
                lesson = load_first_week(order)
                self.assertEqual(lesson["order"], order)
                self.assertEqual(lesson["level"], "A1")
                self.assertEqual(lesson["week"], 1)
                self.assertEqual([l["number"] for l in lesson["layers"]], list(range(1, 8)))
                self.assertEqual([e["order"] for e in lesson["exercises"]],
                                 list(range(1, exercise_count + 1)))
                for exercise in lesson["exercises"]:
                    self.assertTrue(exercise["hint_ru"].strip())
                    self.assertTrue(exercise["explanation_ru"].strip())
                    accepted = exercise.get("accepted", [])
                    self.assertEqual(len(accepted), len(set(accepted)))

    def test_noun_lesson_introduces_labels_and_demonstrative_contrast(self):
        lesson = load_first_week(1)
        intro = layer_text(lesson, 1)
        structure = layer_text(lesson, 3)
        article = layer_text(lesson, 4)
        meanings = layer_text(lesson, 6)

        self.assertIn("существительными", intro)
        self.assertIn("не правило без исключений", intro)
        self.assertIn("Что такое «детерминатив»?", structure)
        self.assertIn("указатель", structure)
        self.assertIn("местоименное употребление", structure)
        self.assertIn("перед book", structure)
        self.assertIn("my не меняется", structure)
        self.assertIn("Так вы уже видели образец для четвёртого задания", structure)
        self.assertIn("[T8]It[/] [D1]is[/] [J2]new[/]", structure)
        self.assertIn("a my book", article)
        self.assertIn("исчисляемому существительному в единственном числе", article)
        self.assertIn("не то же самое, что русские падежные окончания", article)
        self.assertIn("одной порции кофе", meanings)
        self.assertIn("I like coffee", meanings)

    def test_noun_transfer_prompt_matches_accepted_answers(self):
        lesson = load_first_week(1)
        first = next(e for e in lesson["exercises"] if e["order"] == 1)
        self.assertEqual(first["prompt_en"], "This is my new phone.")
        self.assertNotIn("have", first["options"])
        exercise = next(e for e in lesson["exercises"] if e["order"] == 4)
        self.assertIn("одной или двумя", exercise["prompt_ru"])
        self.assertIn("This is my new book.", exercise["accepted"])
        self.assertNotIn("This is my book, it is new.", exercise["accepted"])

    def test_be_lesson_distinguishes_full_sentences_and_short_replies(self):
        lesson = load_first_week(2)
        intro = layer_text(lesson, 1)
        structure = layer_text(lesson, 3)
        questions = layer_text(lesson, 4)
        spoken = layer_text(lesson, 5)
        edge_cases = layer_text(lesson, 6)
        guidance = layer_text(lesson, 7)

        self.assertIn("полных утверждениях", intro)
        self.assertIn("I like coffee", intro)
        self.assertIn("Water, please", intro)
        self.assertIn("подлежащим", structure)
        self.assertIn("This или it?", structure)
        self.assertIn("It is not", questions)
        self.assertIn("Is it", questions)
        self.assertIn("дополнительное слово", questions)
        self.assertIn("you're и your", spoken)
        self.assertIn("Yes, it is", spoken)
        self.assertIn("I'm home", edge_cases)
        self.assertIn("I am at home", edge_cases)
        self.assertIn("Пять заданий", guidance)

    def test_unqualified_old_generalizations_do_not_return(self):
        combined = "\n".join(
            layer["body"] for order in (1, 2)
            for layer in load_first_week(order)["layers"]
        )
        for old_claim in (
            "В каждом предложении должен стоять глагол.",
            "a coffee там означает «чашка кофе». Это нормально, но только в заказе.",
            "после глаголов движения «домой» предлог не нужен",
            "Полные формы звучат подчёркнуто, официально или сердито.",
        ):
            with self.subTest(claim=old_claim):
                self.assertNotIn(old_claim, combined)
