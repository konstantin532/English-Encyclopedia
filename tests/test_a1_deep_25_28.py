"""Live answer/progress contracts for the final A1 group; same cases before/after."""
import json
from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase
from apps.drills.models import Exercise, PracticeItem
from apps.learning.models import UnitProgress
from apps.learning.micro_review import micro_bank
from tests.runner import ensure_content


class FinalA1DeepAPI(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def check(self, item, answer, expected):
        kind = 'practice' if isinstance(item, PracticeItem) else 'exercises'
        result = self.client.post(f'/api/{kind}/{item.pk}/check/', json.dumps({'answer': answer}), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['correct'], expected, answer)

    def test_language_order_does_not_change_ability(self):
        item = Exercise.objects.get(uid='EX-00143')
        for text, expected in [
            ('Yes, I can. I can speak English and Russian.', True),
            ('Yes, I can. I speak English and Russian.', True),
            ('Yes, I can.', True),
            ('No, I cannot speak English.', False),
            ('Yes, I can. I can speak Russian.', False),
            ('Yes, I can. I can speaks English and Russian.', False),
        ]:
            with self.subTest(text=text):
                self.check(item, text, expected)

    def test_name_contraction_is_local_and_preserves_owner_origin(self):
        item = PracticeItem.objects.get(lesson__slug='a1-review-everything', order=1)
        for text, expected in [
            ("My name's Anna. I am from Russia.", True),
            ("My name is Anna. I'm from Russia.", True),
            ("Your name's Anna. I am from Russia.", False),
            ("My name's Anna. I am not from Russia.", False),
            ("My name's Anna. Russia is from me.", False),
        ]:
            with self.subTest(text=text):
                self.check(item, text, expected)

    def test_answered_destination_arrival_and_weather_only(self):
        for i, (uid, answer, required, forbidden) in enumerate([
            ('EX-00155', 'Does this bus go to the park?', {'LX-00252'}, {'LX-00255'}),
            ('EX-00156', 'Поезд прибывает в шесть.', {'LX-00464', 'LX-00472'}, {'LX-00473'}),
            ('EX-00162', 'It is sunny today.', {'LX-00458'}, {'LX-00457'}),
        ]):
            with self.subTest(uid=uid):
                user = get_user_model().objects.create_user(email=f'final-deep-{i}@example.test', password='test-pass')
                self.client.force_login(user)
                self.check(Exercise.objects.get(uid=uid), answer, True)
                trained = set(UnitProgress.objects.filter(user=user).values_list('unit__uid', flat=True))
                self.assertTrue(required <= trained, trained)
                self.assertFalse(forbidden & trained, trained)

    def test_question_order_and_negative_reason_stay_required(self):
        for uid, yes, no in [
            ('EX-00142', 'Can you teach me', 'You can teach me'),
            ('EX-00154', 'What time is the next bus', 'What time the next bus is'),
            ('EX-00163', 'I want to buy an umbrella because I do not like rain.', 'I want to buy an umbrella because I like rain.'),
        ]:
            with self.subTest(uid=uid):
                item = Exercise.objects.get(uid=uid)
                self.check(item, yes, True)
                self.check(item, no, False)


class FinalA1DeepGeneratedReview(SimpleTestCase):
    def test_generated_contexts_have_russian_case_and_preposition(self):
        bank = micro_bank()
        self.assertFalse(any('В встрече' in row[0] for row in bank['a1-can-skills']['1']))
        self.assertFalse(any('Вам нужен школа' in row[0] or 'Вам нужен станция' in row[0] for row in bank['a1-bus-ticket']['4']))


class FinalA1DeepPoemHTML(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_open_shop_has_adjective_marker_in_actual_page(self):
        from html.parser import HTMLParser
        from django.urls import reverse
        user = get_user_model().objects.create_user(email='poem-final@example.test', password='test-pass')
        self.client.force_login(user)
        response = self.client.get(reverse('stories:poem', args=[7]))
        self.assertEqual(response.status_code, 200)
        class MarkedWords(HTMLParser):
            def __init__(self):
                super().__init__()
                self.attrs = None
                self.words = []
            def handle_starttag(self, tag, attrs):
                if tag == 'span':
                    self.attrs = dict(attrs)
            def handle_data(self, data):
                if self.attrs and data == 'open':
                    self.words.append((self.attrs.get('data-cat'), self.attrs.get('data-cls')))
            def handle_endtag(self, tag):
                if tag == 'span':
                    self.attrs = None
        parser = MarkedWords()
        parser.feed(response.content.decode())
        self.assertIn(('J', '2'), parser.words)
        self.assertNotIn(('D', '2'), parser.words)
