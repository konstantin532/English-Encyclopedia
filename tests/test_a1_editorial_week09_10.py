"""Live grading and review regressions for A1 lessons 17–20."""
import json
from django.test import TestCase, SimpleTestCase
from apps.drills.models import PracticeItem, Exercise
from apps.learning.micro_review import micro_bank
from tests.runner import ensure_content


class A1WeekNineTenAnswerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def check_practice(self, slug, order, answer, expected):
        item = PracticeItem.objects.get(lesson__slug=slug, order=order)
        response = self.client.post(f'/api/practice/{item.pk}/check/',
                                   json.dumps({'answer': answer}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['correct'], expected, answer)

    def test_polite_spelling_request(self):
        for answer, expected in (
            ('Please spell your last name.', True),
            ('Can you spell your last name, please?', True),
            ('Please call your last name.', False),
        ):
            with self.subTest(answer=answer):
                self.check_practice('a1-spelling-phone-numbers', 1, answer, expected)

    def test_frequency_and_day_can_change_position(self):
        for answer, expected in (
            ('On Saturdays, I always read.', True),
            ('I always read Saturdays.', True),
            ('I never read on Saturdays.', False),
        ):
            with self.subTest(answer=answer):
                self.check_practice('a1-always-never', 1, answer, expected)

    def test_sometimes_can_follow_the_object(self):
        item = Exercise.objects.get(uid='EX-00106')
        for answer, expected in (
            ('I play the guitar sometimes', True),
            ('Sometimes I play the guitar', True),
            ('I sometimes plays the guitar', False),
        ):
            with self.subTest(answer=answer):
                response = self.client.post(f'/api/exercises/{item.pk}/check/',
                    json.dumps({'answer': answer}), content_type='application/json')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['correct'], expected, answer)

    def test_translation_review_matches_skill(self):
        for slug, expected in {
            'a1-questions-do-does': [2, 3, 2, 4],
            'a1-spelling-phone-numbers': [1, 3, 5, 6],
            'a1-always-never': [2, 1, 4, 2],
            'a1-like-doing': [1, 4, 3, 4],
        }.items():
            with self.subTest(slug=slug):
                self.assertEqual(list(PracticeItem.objects.filter(lesson__slug=slug)
                    .order_by('order').values_list('review_of', flat=True)), expected)

    def test_phone_translation_distinguishes_call_and_text(self):
        for answer, expected in [('Call me later.', True), ('Please call me later.', True),
                                 ('Text me later.', False)]:
            with self.subTest(answer=answer):
                self.check_practice('a1-spelling-phone-numbers', 4, answer, expected)


    def test_key_question_records_relevant_vocabulary_progress(self):
        from django.contrib.auth import get_user_model
        from apps.learning.models import UnitProgress
        user = get_user_model().objects.create_user(email='editorial-key-learner@example.test', password='test-pass')
        self.client.force_login(user)
        self.check_practice('a1-questions-do-does', 1, 'Do you have my key?', True)
        practiced = set(UnitProgress.objects.filter(user=user).values_list('unit__uid', flat=True))
        self.assertIn('LX-00033', practiced)  # have
        self.assertIn('LX-00160', practiced)  # key
        self.assertNotIn('LX-00192', practiced)  # See you! was never answered


class A1QuestionReviewGrammarTests(SimpleTestCase):
    def test_does_distractor_puts_s_on_verb_not_final_noun(self):
        rows = micro_bank()['a1-questions-do-does']['4']
        self.assertIn('Does Mia works every day?', rows[0][2])
        self.assertNotIn('Does Mia work every days?', rows[0][2])
        self.assertIn('Does Tom drinks tea in the morning?', rows[1][2])

    def test_fallback_review_preserves_place_and_has_one_correct_option(self):
        # Exercise the production fallback loader: completed micro packs normally
        # override these cards, but the fallback must remain semantically valid.
        from unittest.mock import patch
        from apps.learning.mistake_review import question_bank
        question_bank.cache_clear()
        try:
            with patch('apps.learning.mistake_review.micro_bank', return_value={}):
                row = question_bank()['a1-always-never']['1'][2]
                self.assertIn('в парке', row[0])
                self.assertNotIn('после обеда', row[0])
                self.assertEqual(row[2][row[3]], 'I sometimes walk in the park.')
                self.assertNotIn('I walk sometimes in the park.', row[2])
        finally:
            question_bank.cache_clear()
