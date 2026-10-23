"""Behavioral regressions for actual lesson keys, not grammar certification."""
import json

from django.test import TestCase

from apps.drills.models import Exercise, PracticeItem
from tests.runner import ensure_content


class GrammarAnswerIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def check_answer(self, collection, item, answer, expected):
        response = self.client.post(
            f"/api/{collection}/{item.pk}/check/",
            json.dumps({"answer": answer}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["correct"], expected)

    def test_taught_valid_alternatives_are_accepted(self):
        for uid, answer in (
            ("EX-00109", "Friday"),
            ("EX-00107", "I never work on Sundays."),
            ("EX-00113", "I like to play the guitar."),
            ("EX-00237", "any"),
        ):
            with self.subTest(uid=uid, answer=answer):
                self.check_answer("exercises", Exercise.objects.get(uid=uid), answer, True)
        for slug, order, answer in (
            ("a1-like-doing", 4, "I play guitar on Sundays."),
            ("a1-can-skills", 3, "I can't play guitar."),
        ):
            with self.subTest(slug=slug, answer=answer):
                item = PracticeItem.objects.get(lesson__slug=slug, order=order)
                self.check_answer("practice", item, answer, True)

    def test_movement_blank_requires_a_word_not_a_second_sentence(self):
        item = Exercise.objects.get(uid="EX-00323")
        self.check_answer("exercises", item, "across", True)
        # Full translation is valid by itself, but not inside Go ___ the street.
        self.check_answer("exercises", item, "Cross the street.", False)
