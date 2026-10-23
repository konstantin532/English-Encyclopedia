"""Targeted editorial regressions; these are not a certification of all lessons."""
from pathlib import Path

import yaml
from django.conf import settings
from django.test import SimpleTestCase


LESSONS = Path(settings.BASE_DIR) / "content" / "seed_lessons"


def lesson(filename):
    return yaml.safe_load((LESSONS / filename).read_text(encoding="utf-8"))


class A1A1PlusSemanticRegressions(SimpleTestCase):
    def test_present_simple_not_conflated_with_right_now(self):
        data = lesson("a1_w10_l19_always_never.yaml")
        note = data["contractions"][0]["note_ru"]
        self.assertNotIn("не гуляю (сейчас, обычно)", note)
        self.assertIn("Present Simple", note)
        explanation = data["layers"][3]["body"]
        self.assertIn("I don't work on Sundays", explanation)
        self.assertIn("I never work on Sundays", explanation)

    def test_you_is_both_singular_and_plural(self):
        data = lesson("a1p_w02_l03_was_were.yaml")
        explanation = data["layers"][3]["body"]
        self.assertIn("одного собеседника", explanation)
        self.assertIn("нескольких", explanation)
        self.assertIn("you were", explanation)

    def test_per_day_is_not_misdescribed_as_literal_each(self):
        data = lesson("a1p_w11_l21_how_often.yaml")
        explanation = data["layers"][3]["body"]
        self.assertIn("единицу периода", explanation)
        self.assertIn("twice in one day", explanation.casefold())
        self.assertIn("два события **в пределах одного дня**", explanation)

    def test_first_conditional_rule_is_scoped(self):
        data = lesson("a1p_w15_l29_if_will.yaml")
        exercise = next(e for e in data["exercises"] if e["uid"] == "EX-00332")
        self.assertIn("в изучаемой схеме", exercise["explanation_ru"])
        self.assertIn("не запрет", exercise["explanation_ru"].lower())

    def test_impersonal_it_applies_to_a_full_statement(self):
        data = lesson("a1p_w02_l04_there_was.yaml")
        practice = next(e for e in data["practice"] if e["answer"] == "It was very interesting.")
        explanation = practice["explanation_ru"]
        self.assertIn("В таком полном предложении", explanation)
        self.assertIn("подлежащее it", explanation)
        self.assertIn("короткие самостоятельные реплики", explanation)
