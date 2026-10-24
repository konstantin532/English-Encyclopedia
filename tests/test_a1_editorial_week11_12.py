"""Meaning, persisted progress and review regressions for A1 lessons 21–24."""
import json
from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from apps.drills.models import PracticeItem, Exercise
from apps.learning.models import UnitProgress, IndependentAttempt
from apps.learning.understanding import understanding_bank
from apps.learning.micro_review import micro_bank
from tests.runner import ensure_content


class A1HealthPostAnswerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def check_practice(self, slug, order, answer, expected):
        item = PracticeItem.objects.get(lesson__slug=slug, order=order)
        response = self.client.post(f'/api/practice/{item.pk}/check/',
            json.dumps({'answer': answer}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['correct'], expected, answer)

    def test_independent_headache_accepts_both_taught_constructions(self):
        user = get_user_model().objects.create_user(email='headache@example.test', password='test-pass')
        self.client.force_login(user)
        slug = 'a1-what-hurts'
        guide = understanding_bank()[slug]
        url = reverse('learning:independent_check', args=[slug])
        for answer, expected in [('I have a headache.', True), ('My head hurts.', True),
                                 ('I have headache.', False)]:
            with self.subTest(answer=answer):
                initial = self.client.get(url)
                form = {'action': 'batch', 'assistance': 'no_help',
                        'batch_token': initial.context['batch_token'],
                        'transfer_variant': str(initial.context['transfer_variant'])}
                for skill in ('meaning', 'writing', 'transfer', 'explain'):
                    form['answer_' + skill] = guide['tasks'][skill]['model']
                form['answer_writing'] = answer
                response = self.client.post(url, form)
                self.assertEqual(response.status_code, 200)
                attempt = IndependentAttempt.objects.filter(user=user, skill='writing').latest('pk')
                self.assertEqual(attempt.outcome == IndependentAttempt.Outcome.MODEL_MATCH, expected)

    def test_plural_body_part_translation(self):
        for answer, expected in [('My feet hurt.', True), ('My feet hurts.', False)]:
            with self.subTest(answer=answer):
                self.check_practice('a1-what-hurts', 3, answer, expected)

    def test_full_negative_is_a_valid_reply(self):
        item = Exercise.objects.get(uid='EX-00131')
        for answer, expected in [('I do not know.', True), ("I don't know.", True),
                                 ('I not know.', False)]:
            with self.subTest(answer=answer):
                response = self.client.post(f'/api/exercises/{item.pk}/check/',
                    json.dumps({'answer': answer}), content_type='application/json')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['correct'], expected)

    def test_negative_translations_record_only_relevant_progress(self):
        cases = (
            ('a1-what-hurts', 4, 'My leg hurts.', {'LX-00400'}, {'LX-00216', 'LX-00408'}),
            ('a1-cant-cannot', 2, "You can't work at night.", {'LX-00218', 'LX-00128'}, {'LX-00224'}),
            ('a1-dont-doesnt', 1, "I don't have a stamp.", {'LX-00233'}, {'LX-00235', 'LX-00236'}),
            ('a1-dont-doesnt', 3, "I don't know.", {'LX-00229', 'LX-00236'}, {'LX-00233', 'LX-00235'}),
            ('a1-letters-address', 4, 'The address is on the envelope.', {'LX-00227', 'LX-00416'}, {'LX-00232'}),
        )
        for index, (slug, order, answer, required, forbidden) in enumerate(cases):
            with self.subTest(slug=slug, order=order):
                user = get_user_model().objects.create_user(email=f'progress{index}@example.test', password='test-pass')
                self.client.force_login(user)
                self.check_practice(slug, order, answer, True)
                practiced = set(UnitProgress.objects.filter(user=user).values_list('unit__uid', flat=True))
                self.assertTrue(required <= practiced, practiced)
                self.assertFalse(forbidden & practiced, practiced)

    def test_postal_exercises_do_not_credit_an_unrelated_stamp_or_letter(self):
        for index, (uid, answer, required, forbidden) in enumerate((
            ('EX-00132', "Tom doesn't have an envelope.", {'LX-00416'}, {'LX-00233'}),
            ('EX-00137', 'It is for my friend in Russia.', {'LX-00164'}, {'LX-00225'}),
        )):
            with self.subTest(uid=uid):
                user = get_user_model().objects.create_user(email=f'exercise{index}@example.test', password='test-pass')
                self.client.force_login(user)
                exercise = Exercise.objects.get(uid=uid)
                response = self.client.post(f'/api/exercises/{exercise.pk}/check/',
                    json.dumps({'answer': answer}), content_type='application/json')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()['correct'])
                practiced = set(UnitProgress.objects.filter(user=user).values_list('unit__uid', flat=True))
                self.assertTrue(required <= practiced, practiced)
                self.assertFalse(forbidden & practiced, practiced)

    def test_reviews_follow_the_translation_skill(self):
        for slug, expected in {
            'a1-what-hurts': [2, 1, 5, 6],
            'a1-cant-cannot': [2, 1, 1, 1],
            'a1-dont-doesnt': [2, 1, 4, 3],
            'a1-letters-address': [4, 1, 2, 1],
        }.items():
            with self.subTest(slug=slug):
                self.assertEqual(list(PracticeItem.objects.filter(lesson__slug=slug)
                    .order_by('order').values_list('review_of', flat=True)), expected)


class A1HealthPostReviewTests(SimpleTestCase):
    def test_negative_distractor_conjugates_verb_not_object(self):
        bank = micro_bank()['a1-dont-doesnt']
        self.assertIn("He doesn't gets letters.", bank['1'][0][2])
        self.assertNotIn("He doesn't get letterss.", bank['1'][0][2])
        self.assertIn("My friend doesn't watches TV.", bank['3'][3][2])

    def test_headache_review_uses_known_a1_complaints(self):
        rows = micro_bank()['a1-what-hurts']['2']
        for row in rows:
            self.assertEqual(row[2][row[3]], 'headache')
        self.assertEqual(len({row[0] for row in rows}), 5)

    def test_fallback_but_card_has_an_explicit_contrast(self):
        from unittest.mock import patch
        from apps.learning.mistake_review import question_bank
        question_bank.cache_clear()
        try:
            with patch('apps.learning.mistake_review.micro_bank', return_value={}):
                row = question_bank()['a1-cant-cannot']['1'][2]
                self.assertIn('Голова не болит', row[0])
                self.assertEqual(row[2][row[3]], 'But my back hurts.')
        finally:
            question_bank.cache_clear()
