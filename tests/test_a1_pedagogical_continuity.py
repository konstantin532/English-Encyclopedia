"""Контроль непрерывности объяснений в уроках 3–26 A1.

Смысл тестов — защищать конкретные исправленные методические разрывы и
грамматические ограничения, а не выдавать автотест за оценку понятности
объяснений реальными учениками.
"""
from pathlib import Path
import re

import yaml
from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[1] / "content" / "seed_lessons"
FILES = {
    3: "a1_w02_l03_determiners.yaml",
    4: "a1_w02_l04_have_like_can.yaml",
    5: "a1_w03_l05_cafe.yaml",
    6: "a1_w03_l06_numbers.yaml",
    7: "a1_w04_l07_family.yaml",
    8: "a1_w04_l08_possession.yaml",
    9: "a1_w05_l09_there_is.yaml",
    10: "a1_w05_l10_how_much.yaml",
    11: "a1_w06_l11_present_simple.yaml",
    12: "a1_w06_l12_time.yaml",
    13: "a1_w07_l13_he_works.yaml",
    14: "a1_w07_l14_jobs.yaml",
    15: "a1_w08_l15_where_is.yaml",
    16: "a1_w08_l16_directions.yaml",
    17: "a1_w09_l17_do_does.yaml",
    18: "a1_w09_l18_spelling.yaml",
    19: "a1_w10_l19_always_never.yaml",
    20: "a1_w10_l20_like_doing.yaml",
    21: "a1_w11_l21_what_hurts.yaml",
    22: "a1_w11_l22_cant.yaml",
    23: "a1_w12_l23_dont_doesnt.yaml",
    24: "a1_w12_l24_address.yaml",
    25: "a1_w13_l25_can_skills.yaml",
    26: "a1_w13_l26_why_because.yaml",
}

# Минимальные смысловые опоры, которые нельзя незаметно выбросить при
# следующей редактуре. Не требуем дословного совпадения целого абзаца.
CONCEPT_CHECKS = {
    3: ("может определить", "единственном числе", "местоимения"),
    4: ("модальный глагол", "вспомогательный глагол", "I like"),
    5: ("не всегда грубое", "I'd like", "две порции"),
    6: ("порции", "не означает", "ударение может меняться"),
    7: ("He is ten", "baby brother", "hundred"),
    8: ("own", "получателя действия", "Mia's photo"),
    9: ("о наличии", "Неисчисляемость зависит от значения", "some"),
    10: ("How many apples?", "цене", "dollars"),
    11: ("вопроса и отрицания", "I am working", "get up"),
    12: ("Который час?", "Во сколько?", "seven hours"),
    13: ("грамматическую работу", "Does he work", "Works from home"),
    14: ("не подходит", "What do you do?", "at a hospital"),
    15: ("непосредственно рядом", "on the street", "предлог"),
    16: ("повелительное наклонение", "подлежащего", "дополнения"),
    17: ("перед подлежащим", "Who works here?", "This is Anna"),
    18: ("семизначный учебный фрагмент", "названия букв", "написание фамилии"),
    19: ("стандартном американском английском", "диалектах", "on the weekend"),
    20: ("герундием", "I like to read", "play guitar"),
    21: ("две привычные английские конструкции", "my feet hurt", "подлежащее"),
    22: ("не имеет отчётливого взрыва", "cannot", "can't"),
    23: ("there isn't", "смысловой глагол", "стандартном американском английском"),
    24: ("почтового адреса США", "перед названием улицы", "USPS"),
    25: ("образец для Анны", "владением языком", "начальной форме"),
    26: ("цели", "because of", "придаточную часть причины"),
}


def read_lesson(number):
    return yaml.safe_load((ROOT / FILES[number]).read_text(encoding="utf-8"))


class A1PedagogicalContinuityTests(SimpleTestCase):
    def test_all_edited_lessons_have_stable_seven_layer_outline(self):
        self.assertEqual(set(FILES), set(range(3, 27)))
        for number in FILES:
            with self.subTest(lesson=number):
                lesson = read_lesson(number)
                self.assertEqual(lesson["level"], "A1")
                self.assertEqual(lesson["order"], number)
                self.assertEqual(lesson["week"], (number + 1) // 2)
                self.assertEqual([x["number"] for x in lesson["layers"]], list(range(1, 8)))
                expected = 5 if number in (3, 4) else 4 if number == 6 else 6
                self.assertEqual([x["order"] for x in lesson["exercises"]],
                                 list(range(1, expected + 1)))
                for exercise in lesson["exercises"]:
                    self.assertTrue(exercise.get("hint_ru", "").strip())
                    self.assertTrue(exercise.get("explanation_ru", "").strip())

    def test_markup_balance_retained(self):
        for number in FILES:
            with self.subTest(lesson=number):
                body = "\n".join(layer["body"] for layer in read_lesson(number)["layers"])
                self.assertEqual(len(re.findall(r"\[[A-Z]\d+\]", body)), body.count("[/]"))

    def test_necessary_explanatory_bridges_remain(self):
        for number, terms in CONCEPT_CHECKS.items():
            lesson = read_lesson(number)
            body = "\n".join(layer["body"] for layer in lesson["layers"])
            for term in terms:
                with self.subTest(lesson=number, concept=term):
                    self.assertIn(term.casefold(), body.casefold())

    def test_week_six_scene_keeps_question_answer_pairs(self):
        lesson = read_lesson(11)
        speech = lesson["layers"][4]["body"]
        self.assertLess(speech.index("Во сколько ты встаёшь"), speech.index("Я встаю в пять"))
        self.assertLess(speech.index("Я встаю в пять"), speech.index("А ты завтракаешь?"))
        self.assertLess(speech.index("А ты завтракаешь?"), speech.index("Да. Я завтракаю"))
        self.assertIn("Нельзя использовать *Yes, I do* как ответ на вопрос", speech)

    def test_transfer_checks_accept_only_requested_action(self):
        phone_lesson = read_lesson(18)
        callback = next(x for x in phone_lesson["exercises"] if x["order"] == 6)
        self.assertEqual(callback["answer"], "Call me later.")
        self.assertNotIn("Text me later.", callback.get("accepted", []))

        determiners = read_lesson(3)
        two_rooms = next(x for x in determiners["exercises"] if x["order"] == 5)
        self.assertNotIn("This room is big, that room is new.", two_rooms.get("accepted", []))

        abilities = read_lesson(25)
        abilities_transfer = next(x for x in abilities["exercises"] if x["order"] == 4)
        self.assertIn("коротко", abilities_transfer["prompt_ru"])
        self.assertIn("Yes, I can.", abilities_transfer["accepted"])

    def test_overbroad_rules_not_reintroduced(self):
        banned = {
            9: ("предлог стоит перед словом всегда", "всю работу делает предлог"),
            11: ("потому что глаголу не нужны помощники",),
            14: ("Если сейчас не работаете, можно сказать: I work at home",),
            18: ("Номер телефона в США — 10 цифр: код города и 7 цифр, например 555-2146",),
            19: ("одно отрицание отменяет другое",),
            22: ("t в конце американцы почти не произносят",),
        }
        for number, phrases in banned.items():
            body = "\n".join(layer["body"] for layer in read_lesson(number)["layers"])
            for phrase in phrases:
                with self.subTest(lesson=number, phrase=phrase):
                    self.assertNotIn(phrase, body)
