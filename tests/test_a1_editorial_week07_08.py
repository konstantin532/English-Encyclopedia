"""Live grading regressions for A1 lessons 13–16."""
import json
from django.test import TestCase
from apps.drills.models import PracticeItem
from tests.runner import ensure_content


class A1WeekSevenEightAnswerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def check(self, slug, order, answer, expected):
        item = PracticeItem.objects.get(lesson__slug=slug, order=order)
        response = self.client.post(
            f'/api/practice/{item.pk}/check/',
            json.dumps({'answer': answer}), content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['correct'], expected, answer)

    def test_polite_attention_getters(self):
        for answer, expected in (
            ('Sorry, where is the bank?', True),
            ('Excuse me, where is the bank?', True),
            ('Sorry, what is the bank?', False),
        ):
            with self.subTest(answer=answer):
                self.check('a1-directions-turn-left', 4, answer, expected)

    def test_between_endpoints_can_be_reversed(self):
        for answer, expected in (
            ('The bank is between the hotel and the cafe.', True),
            ('The bank is between the cafe and the hotel.', True),
            ('The hotel is between the cafe and the bank.', False),
        ):
            with self.subTest(answer=answer):
                self.check('a1-where-is-prepositions', 4, answer, expected)

    def test_translation_review_returns_to_the_relevant_skill(self):
        expected = {
            'a1-he-she-works': [1, 1, 3, 6],
            'a1-jobs-what-do-you-do': [2, 3, 1, 2],
            'a1-where-is-prepositions': [1, 3, 4, 5],
            'a1-directions-turn-left': [2, 1, 3, 4],
        }
        for slug, orders in expected.items():
            with self.subTest(slug=slug):
                items = PracticeItem.objects.filter(lesson__slug=slug).order_by('order')
                self.assertEqual(list(items.values_list('review_of', flat=True)), orders)
