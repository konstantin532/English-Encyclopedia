"""Week 5 answer variants through the learner-facing check endpoints."""

import json

from django.test import TestCase

from apps.drills.models import Exercise, PracticeItem
from tests.runner import ensure_content


class A1WeekFiveAnswerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def check(self, collection, item, answer, expected):
        response = self.client.post(
            f"/api/{collection}/{item.pk}/check/",
            json.dumps({"answer": answer}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["correct"], expected)

    def test_apples_price_transfer_requires_full_plural_response(self):
        item = Exercise.objects.get(uid="EX-00053")
        self.assertEqual(item.answer, "They are five dollars.")
        self.assertIn("They're five dollars.", item.accepted)
        # Singular and short replies can be valid English, but this task asks
        # for a full response beginning with They to practice plural agreement.
        cases = [
            ("They are five dollars.", True),
            ("They're five dollars.", True),
            ("They is five dollars.", False),
            ("They are five dollar.", False),
            ("They are two dollars.", False),
            ("It is five dollars.", False),
            ("Five dollars.", False),
        ]
        for answer, expected in cases:
            with self.subTest(answer=answer):
                self.check("exercises", item, answer, expected)

    def test_apples_availability_accepts_some_and_preserves_agreement(self):
        item = PracticeItem.objects.get(lesson__slug="a1-there-is-some", order=2)
        cases = [
            ("There are some apples.", True),
            ("There is some apples.", False),
            ("There are no apples.", False),
        ]
        for answer, expected in cases:
            with self.subTest(answer=answer):
                self.check("practice", item, answer, expected)

    def test_cat_food_absence_preserves_the_requested_negative_pattern(self):
        item = PracticeItem.objects.get(lesson__slug="a1-there-is-some", order=3)
        cases = [
            ("There is no cat food.", True),
            ("There's no cat food.", True),
            ("There is some cat food.", False),
        ]
        for answer, expected in cases:
            with self.subTest(answer=answer):
                self.check("practice", item, answer, expected)

    def test_milk_price_accepts_article_variants(self):
        item = PracticeItem.objects.get(lesson__slug="a1-how-much-prices", order=1)
        cases = [
            ("How much is the milk?", True),
            ("How much is milk?", True),
            ("How much are the milk?", False),
        ]
        for answer, expected in cases:
            with self.subTest(answer=answer):
                self.check("practice", item, answer, expected)

