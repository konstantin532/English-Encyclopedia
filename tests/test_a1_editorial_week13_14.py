"""Answer contracts and persisted progress for the last four A1 lessons."""
import json

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.drills.models import Exercise, PracticeItem
from apps.learning.micro_review import micro_bank
from apps.learning.models import IndependentAttempt, UnitProgress
from apps.learning.understanding import understanding_bank
from tests.runner import ensure_content


class A1FinalAnswersTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def check_answer(self, item, answer, expected=True):
        kind = 'practice' if isinstance(item, PracticeItem) else 'exercises'
        response = self.client.post(f'/api/{kind}/{item.pk}/check/',
            json.dumps({'answer': answer}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['correct'], expected, answer)

    def test_taught_and_coordinated_answers(self):
        for uid, answers in {
            'EX-00157': ["Where's the train station?", "Excuse me, where's the train station?"],
            'EX-00161': ['I am from Russia and I can speak English.',
                         "I'm from Russia and I speak English."],
            'EX-00163': ['I want to buy an umbrella because I do not like rain.'],
        }.items():
            for answer in answers:
                with self.subTest(uid=uid, answer=answer):
                    self.check_answer(Exercise.objects.get(uid=uid), answer)
        self.check_answer(PracticeItem.objects.get(
            lesson__slug='a1-review-everything', order=1), "My name's Anna. I'm from Russia.")

    def test_short_answer_preserves_can_and_plural_tickets(self):
        item = Exercise.objects.get(uid='EX-00141')
        self.check_answer(item, 'can')
        self.check_answer(item, 'do', False)
        item = Exercise.objects.get(uid='EX-00153')
        self.check_answer(item, 'tickets')
        self.check_answer(item, 'ticket', False)

    def test_independent_reason_accepts_full_and_contracted_be(self):
        user = get_user_model().objects.create_user(email='reason@example.test', password='test-pass')
        self.client.force_login(user)
        slug = 'a1-why-because'
        guide = understanding_bank()[slug]
        url = reverse('learning:independent_check', args=[slug])
        for answer, matches in [('Because I am tired.', True), ("Because I'm tired.", True),
                                ('Because I tired.', False)]:
            with self.subTest(answer=answer):
                initial = self.client.get(url)
                form = {'action': 'batch', 'assistance': 'no_help',
                        'batch_token': initial.context['batch_token'],
                        'transfer_variant': str(initial.context['transfer_variant'])}
                for skill in ('meaning', 'writing', 'transfer', 'explain'):
                    form['answer_' + skill] = guide['tasks'][skill]['model']
                form['answer_writing'] = answer
                self.assertEqual(self.client.post(url, form).status_code, 200)
                attempt = IndependentAttempt.objects.filter(user=user, skill='writing').latest('pk')
                self.assertEqual(attempt.outcome == IndependentAttempt.Outcome.MODEL_MATCH, matches)

    def test_translations_credit_only_the_answered_skill(self):
        cases = [
            ('a1-can-skills', 1, 'I can speak Russian.', {'LX-00239', 'LX-00244'}, {'LX-00248', 'LX-00249', 'LX-00251'}),
            ('a1-can-skills', 3, "I can't play the guitar.", {'LX-00218', 'LX-00202', 'LX-00204'}, {'LX-00248', 'LX-00251'}),
            ('a1-why-because', 2, "Because I can't sleep.", {'LX-00242', 'LX-00217'}, {'LX-00250'}),
            ('a1-why-because', 3, 'Why do you want to learn Russian?', {'LX-00241', 'LX-00434'}, {'LX-00250'}),
            ('a1-bus-ticket', 1, 'Does this bus go to Park Street?', {'LX-00255'}, {'LX-00258'}),
            ('a1-bus-ticket', 2, 'How much is a ticket?', {'LX-00256'}, {'LX-00258'}),
            ('a1-bus-ticket', 4, 'What time is the next bus?', {'LX-00258'}, {'LX-00255', 'LX-00256'}),
            ('a1-review-everything', 1, 'I am Anna. I am from Russia.', {'LX-00045'}, {'LX-00256', 'LX-00258', 'LX-00176', 'LX-00236'}),
            ('a1-review-everything', 2, 'Can I have coffee, please?', {'LX-00011', 'LX-00035'}, {'LX-00256', 'LX-00236'}),
            ('a1-review-everything', 3, 'Where is the bank? It is on the right.', {'LX-00176', 'LX-00178'}, {'LX-00256', 'LX-00258'}),
        ]
        for index, (slug, order, answer, required, forbidden) in enumerate(cases):
            with self.subTest(slug=slug, order=order):
                user = get_user_model().objects.create_user(email=f'final{index}@example.test', password='test-pass')
                self.client.force_login(user)
                self.check_answer(PracticeItem.objects.get(lesson__slug=slug, order=order), answer)
                practiced = set(UnitProgress.objects.filter(user=user).values_list('unit__uid', flat=True))
                self.assertTrue(required <= practiced, practiced)
                self.assertFalse(forbidden & practiced, practiced)

    def test_core_answers_do_not_credit_bus_route_or_unspoken_languages(self):
        for index, (uid, answer, required, forbidden) in enumerate([
            ('EX-00143', 'Yes, I can.', {'LX-00248'}, {'LX-00239', 'LX-00243', 'LX-00244'}),
            ('EX-00158', 'She works at a school.', {'LX-00128', 'LX-00143'}, {'LX-00255'}),
            ('EX-00161', 'I am from Russia. I speak English.', {'LX-00045', 'LX-00243'}, {'LX-00255', 'LX-00035'}),
        ]):
            with self.subTest(uid=uid):
                user = get_user_model().objects.create_user(email=f'core{index}@example.test', password='test-pass')
                self.client.force_login(user)
                self.check_answer(Exercise.objects.get(uid=uid), answer)
                practiced = set(UnitProgress.objects.filter(user=user).values_list('unit__uid', flat=True))
                self.assertTrue(required <= practiced, practiced)
                self.assertFalse(forbidden & practiced, practiced)

    def test_reviews_follow_the_translation_skill(self):
        for slug, expected in {
            'a1-can-skills': [1, 1, 5, 3], 'a1-why-because': [3, 4, 3, 1],
            'a1-bus-ticket': [1, 2, 2, 3], 'a1-review-everything': [4, 4, 3, 2],
        }.items():
            with self.subTest(slug=slug):
                self.assertEqual(list(PracticeItem.objects.filter(lesson__slug=slug)
                    .order_by('order').values_list('review_of', flat=True)), expected)


class A1FinalReviewTests(SimpleTestCase):
    def test_distractors_change_the_verb_not_the_language_or_negative_phrase(self):
        bank = micro_bank()
        row = bank['a1-can-skills']['5'][4]
        self.assertIn('She can speaks Russian.', row[2])
        self.assertNotIn('She can speak Russians.', row[2])
        for order in ('5', '6'):
            for row in bank['a1-why-because'][order]:
                self.assertFalse(any("doesn't don't" in option for option in row[2]))
                self.assertTrue(any("Because I doesn't " in option for option in row[2]))

    def test_bus_review_has_only_one_grammatical_time_question(self):
        for row in micro_bank()['a1-bus-ticket']['3']:
            self.assertFalse(any('What is the next' in option for option in row[2]))

    def test_final_review_uses_introduced_weather_and_languages(self):
        bank = micro_bank()['a1-review-everything']
        text = json.dumps([bank['4'], bank['5']])
        for unknown in ('rainy', 'Canada', 'France', 'French'):
            self.assertNotIn(unknown, text)
