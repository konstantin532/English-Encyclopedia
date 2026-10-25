"""Behavior regressions for A1 9–12: local keys and honest progress evidence."""
import json

from django.test import TestCase

from apps.accounts.models import User
from apps.drills.models import Exercise, PracticeItem
from apps.learning.models import ExerciseAttempt, UnitProgress
from tests.runner import ensure_content

SLUGS = ('a1-there-is-some', 'a1-how-much-prices',
         'a1-present-simple-i-you', 'a1-time-at-seven')


class A1DeepNineTwelveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.user = User.objects.create_user('deep-nine@example.com', 'test-nine-only')

    def setUp(self):
        self.client.force_login(self.user)

    def check(self, collection, item, text, expected):
        response = self.client.post(f'/api/{collection}/{item.pk}/check/',
                                   json.dumps({'answer': text}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['correct'], expected, text)
        if collection == 'practice' or item.stage == Exercise.Stage.TRANSFER:
            self.assertEqual(data['assessment'], 'model_match' if expected else 'needs_review')

    def test_water_presence_allows_full_contracted_reply_not_changed_polarity(self):
        item = Exercise.objects.get(uid='EX-00047')
        for text, expected in (("Yes, there's water.", True), ("There's water.", True),
                               ('Yes, there is.', True), ("Yes, there's.", False),
                               ("There's no water.", False), ('Yes, there are water.', False),
                               ("There's milk.", False)):
            with self.subTest(answer=text):
                self.check('exercises', item, text, expected)

    def test_apple_price_keeps_the_requested_subject_and_five_dollars(self):
        item = Exercise.objects.get(uid='EX-00053')
        for text, expected in (('They are 5 dollars.', True), ("They're 5 dollars.", True),
                               ("They're five dollars.", True), ('They are four dollars.', False),
                               ('They are not five dollars.', False), ('It is five dollars.', False),
                               ('Five dollars.', False), ('They five dollars are.', False)):
            with self.subTest(answer=text):
                self.check('exercises', item, text, expected)

    def test_evening_actions_allow_shared_i_but_keep_both_actions(self):
        item = Exercise.objects.get(uid='EX-00061')
        for text, expected in (('I watch TV and go to bed early.', True),
                               ('I watch TV. I go to bed early.', True),
                               ('I watch TV and I go to bed early.', True),
                               ('I watch TV and go to bed late.', False),
                               ("I don't watch TV and go to bed early.", False),
                               ('I watch TV.', False), ('You watch TV and go to bed early.', False)):
            with self.subTest(answer=text):
                self.check('exercises', item, text, expected)

    def test_breakfast_time_allows_digits_but_not_different_time_or_meal(self):
        item = Exercise.objects.get(uid='EX-00065')
        for text, expected in (('I have breakfast at 8.', True),
                               ("I have breakfast at 8 o'clock.", True),
                               ("At 8 o'clock.", True), ('At eight.', True),
                               ('I have breakfast at 9.', False), ('I have lunch at 8.', False),
                               ('I have breakfast in 8.', False),
                               ("I don't have breakfast at 8.", False)):
            with self.subTest(answer=text):
                self.check('exercises', item, text, expected)

    def check_practice_credits(self, slug, expected):
        for order, uids in expected.items():
            item = PracticeItem.objects.get(lesson__slug=slug, order=order)
            UnitProgress.objects.filter(user=self.user).delete()
            self.check('practice', item, item.answer, True)
            actual = set(UnitProgress.objects.filter(user=self.user).values_list('unit__uid', flat=True))
            with self.subTest(lesson=slug, translation=order, submitted=item.answer):
                self.assertEqual(actual, set(uids))

    def test_shop_translations_do_not_credit_unspoken_milk_question_or_request(self):
        self.check_practice_credits(SLUGS[0], {
            1: ['LX-00108', 'LX-00112', 'LX-00119'],
            2: ['LX-00109', 'LX-00112'],
            3: ['LX-00111', 'LX-00112'],
            4: ['LX-00109', 'LX-00286'],
        })

    def test_price_questions_do_not_credit_a_price_answer_or_expensive_reaction(self):
        self.check_practice_credits(SLUGS[1], {
            1: ['LX-00114', 'LX-00115', 'LX-00108'],
            2: ['LX-00116', 'LX-00123'],
            3: ['LX-00114', 'LX-00115', 'LX-00109'],
            4: ['LX-00293'],
        })

    def test_daily_routine_translations_do_not_credit_unrelated_full_phrases(self):
        self.check_practice_credits(SLUGS[2], {
            1: ['LX-00124', 'LX-00125', 'LX-00126'],
            2: ['LX-00128', 'LX-00134'],
            3: ['LX-00130', 'LX-00138'],
            4: ['LX-00129', 'LX-00139'],
        })

    def test_clock_question_does_not_credit_a_waking_question_or_clock_answer(self):
        self.check_practice_credits(SLUGS[3], {
            1: ['LX-00132', 'LX-00140'],
            2: ['LX-00303'],
            3: ['LX-00133'],
            4: ['LX-00133', 'LX-00135', 'LX-00124', 'LX-00125', 'LX-00126'],
        })

    def main_credits(self, uid, uids):
        item = Exercise.objects.get(uid=uid)
        self.check('exercises', item, item.answer, True)
        actual = set(UnitProgress.objects.filter(user=self.user).values_list('unit__uid', flat=True))
        self.assertEqual(actual, set(uids))
        saved = ExerciseAttempt.objects.get(user=self.user, exercise=item)
        self.assertEqual(saved.exercise.uid, uid)
        self.assertTrue(saved.is_correct)

    def test_five_dollar_apple_answer_does_not_credit_it_is_two_dollars(self):
        self.main_credits('EX-00053', ['LX-00116'])

    def test_yes_i_do_records_attempt_without_claiming_a_work_or_every_word(self):
        self.main_credits('EX-00059', [])

    def test_filling_at_does_not_claim_an_entire_five_oclock_waking_phrase(self):
        self.main_credits('EX-00063', [])

    def test_breakfast_at_eight_does_not_credit_i_get_up_at_five(self):
        self.main_credits('EX-00065', ['LX-00130'])

    def test_targeted_build_tasks_reject_changed_order_negation_and_subject(self):
        cases = {
            'EX-00046': ('Can I have some apples please', 'Can have I some apples please'),
            'EX-00052': ('How much is the milk', 'How much the milk is'),
            'EX-00058': ('At seven I drink coffee', 'I drink at coffee seven'),
            'EX-00064': ('What time do you get up', 'What time you do get up'),
        }
        for uid, (good, bad) in cases.items():
            item = Exercise.objects.get(uid=uid)
            with self.subTest(uid=uid):
                self.check('exercises', item, good, True)
                self.check('exercises', item, bad, False)
