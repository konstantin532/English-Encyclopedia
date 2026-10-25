"""Behavioral editorial regressions, frozen before the 17–20 corrections."""
import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.drills.models import Exercise, PracticeItem
from apps.learning.models import UnitProgress
from tests.runner import ensure_content

class A1DeepSeventeenTwentyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.user = get_user_model().objects.create_user(email='deep1720@example.test', password='testing')

    def setUp(self):
        self.client.force_login(self.user)

    def submit(self, model, lookup, answer):
        obj = model.objects.get(**lookup)
        kind = 'practice' if model is PracticeItem else 'exercises'
        response = self.client.post(f'/api/{kind}/{obj.pk}/check/', json.dumps({'answer':answer}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        return response.json()['correct']

    def test_practice_semantics_and_ordinary_question_order(self):
        cases = [
            ('a1-questions-do-does', 1, 'Do you have my key?', True),
            ('a1-questions-do-does', 1, 'Do you have your key?', False),
            ('a1-questions-do-does', 1, 'Does you have my key?', False),
            ('a1-questions-do-does', 1, 'You do have my key?', False),
            ('a1-always-never', 2, 'Tom never walks.', True),
            ('a1-always-never', 2, 'Tom always walks.', False),
            ('a1-always-never', 2, "Tom doesn't never walk.", False),
            ('a1-like-doing', 1, 'I like to read.', True),
            ('a1-like-doing', 1, "I don't like reading.", False),
            ('a1-like-doing', 2, 'Tom likes music.', True),
            ('a1-like-doing', 2, 'I like music.', False),
            ('a1-like-doing', 3, 'Do you like to walk?', True),
            ('a1-like-doing', 3, 'Do you likes walking?', False),
            ('a1-like-doing', 4, 'I play guitar on Sundays.', True),
            ('a1-spelling-phone-numbers', 4, 'Call me later.', True),
            ('a1-spelling-phone-numbers', 4, 'Text me later.', False),
        ]
        for slug, order, answer, expected in cases:
            with self.subTest(slug=slug, order=order, answer=answer):
                self.assertEqual(self.submit(PracticeItem, {'lesson__slug':slug,'order':order}, answer), expected)

    def test_ordered_spelling_preserves_letters(self):
        for answer, expected in [('T-O-M.',True), ('T O M',True), ('T, O, M',True), ('T-M-O',False),('M-O-T',False),('Tom',False)]:
            with self.subTest(answer=answer):
                self.assertEqual(self.submit(Exercise, {'uid':'EX-00101'},answer),expected)

    def test_practice_only_credits_demonstrated_units(self):
        cases = [
            ('a1-questions-do-does',3,'Do you work at home?', {'LX-00128','LX-00005'}),
            ('a1-always-never',1,'I always read on Saturdays.',{'LX-00194','LX-00196','LX-00207'}),
            ('a1-always-never',2,'Tom never walks.',{'LX-00197'}),
            ('a1-always-never',3,'I walk in the park on Sundays.',{'LX-00195'}),
            ('a1-always-never',4,'Mia always starts at five.',{'LX-00196'}),
            ('a1-like-doing',1,'I like reading.',{'LX-00200','LX-00208'}),
            ('a1-like-doing',3,'Do you like walking?',{'LX-00201','LX-00209'}),
            ('a1-like-doing',4,'I play the guitar on Sundays.',{'LX-00202','LX-00204','LX-00211'}),
        ]
        for slug,order,answer,expected in cases:
            with self.subTest(slug=slug,order=order):
                UnitProgress.objects.filter(user=self.user).delete()
                self.assertTrue(self.submit(PracticeItem, {'lesson__slug':slug,'order':order},answer))
                self.assertEqual(set(UnitProgress.objects.filter(user=self.user).values_list('unit__uid', flat=True)),expected)

    def test_exercises_do_not_credit_distractors_or_whole_alphabet(self):
        cases = [('EX-00094','What time does the cafe open?',{'LX-00186'}),
                 ('EX-00099','E',set()),('EX-00101','T-O-M.',set()),
                 ('EX-00105','always',{'LX-00196'}),
                 ('EX-00114','jacket',{'LX-00387'})]
        for uid,answer,expected in cases:
            with self.subTest(uid=uid):
                UnitProgress.objects.filter(user=self.user).delete()
                self.assertTrue(self.submit(Exercise, {'uid':uid},answer))
                self.assertEqual(set(UnitProgress.objects.filter(user=self.user).values_list('unit__uid',flat=True)),expected)

    def test_published_pages_preserve_layers_and_role_of_the_speaker(self):
        for slug in ['a1-questions-do-does','a1-spelling-phone-numbers','a1-always-never','a1-like-doing']:
            with self.subTest(slug=slug):
                response=self.client.get(f'/lessons/{slug}/')
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.context['layers'].count(),7)
                self.assertEqual(response.context['lesson'].slug,slug)
        response=self.client.get('/lessons/a1-like-doing/')
        exercise=response.context['exercises'].get(uid='EX-00111')
        self.assertEqual(exercise.prompt_en,'I like ___.')
        self.assertIn('о себе',exercise.prompt_ru)
        self.assertContains(response,'Вы играете роль Анны')

    def test_hobby_alternatives_credit_only_their_shared_skill(self):
        exercise = Exercise.objects.get(uid='EX-00113')
        for answer in [exercise.answer, *exercise.accepted]:
            with self.subTest(answer=answer):
                UnitProgress.objects.filter(user=self.user).delete()
                self.assertTrue(self.submit(Exercise, {'uid':'EX-00113'}, answer))
                self.assertEqual(set(UnitProgress.objects.filter(user=self.user).values_list('unit__uid', flat=True)), {'LX-00034'})
        for answer in ['I play the guitar.', 'I likes music.', "I don't like music.", 'Tom likes music.']:
            with self.subTest(wrong_answer=answer):
                self.assertFalse(self.submit(Exercise, {'uid':'EX-00113'}, answer))
