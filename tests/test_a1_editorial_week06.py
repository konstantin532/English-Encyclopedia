"""Week 6: short-answer checks and review targets at the learner API."""

import json

from django.test import TestCase

from apps.drills.models import Exercise, PracticeItem
from tests.runner import ensure_content


class A1WeekSixEditorialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_habit_question_requires_the_requested_short_answer(self):
        item = Exercise.objects.get(uid="EX-00059")
        for answer, expected in (
            ("Yes, I do.", True),
            ("Yes I do", True),
            ("Yes, I work every day.", False),
        ):
            with self.subTest(answer=answer):
                response = self.client.post(
                    f"/api/exercises/{item.pk}/check/",
                    json.dumps({"answer": answer}),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["correct"], expected)

    def test_practice_review_targets_match_the_skill(self):
        expected = {
            "a1-present-simple-i-you": [3, 1, 2, 3],
            "a1-time-at-seven": [1, 2, 1, 3],
        }
        for slug, targets in expected.items():
            actual = list(
                PracticeItem.objects.filter(lesson__slug=slug)
                .order_by("order").values_list("review_of", flat=True)
            )
            self.assertEqual(actual, targets, slug)
