"""Week 12: postal vocabulary, forms and bounded supplemental practice."""
from django.test import TestCase
from apps.core.a1_active import active_topics
from apps.curriculum.models import WeekScene
from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit
from tests.runner import ensure_content


class WeekTwelveExpansionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_postal_and_address_words_are_taught_in_week_twelve(self):
        expected = {'city', 'country', 'state', 'ZIP code', 'envelope', 'form', 'apartment',
                    'town', 'road', 'mail', 'package', 'postcard', 'wait', 'line', 'large',
                    'heavy', 'light', 'correct', 'fill out', 'sign', 'last name', 'paper'}
        week = LexicalUnit.objects.filter(internal_level__code='A1', week__number=12)
        self.assertEqual(week.count(), 36)
        self.assertTrue(expected <= set(week.values_list('lemma', flat=True)))
        for lesson in Lesson.objects.filter(level__code='A1', order__in=[23,24]):
            self.assertEqual(list(lesson.exercises.order_by('order').values_list('order',flat=True)),[1,2,3,4,5,6])

    def test_dialogue_keeps_mailbox_story_and_introduces_address_vocabulary(self):
        scene = WeekScene.objects.get(week__level__code='A1',week__number=12)
        text = ' '.join(line['text'] for line in scene.script)
        for marked in ('[S4]city[/]', '[S4]country[/]', '[S2]envelope[/]'):
            self.assertIn(marked,text)
        postal = ' '.join(line['text'] for line in scene.script if line['speaker']=='postal')
        self.assertIn('[D1]does[/] [X1]not[/] [D2]get[/] [S9]letters[/]',postal)
        self.assertIn('белое',scene.story_beat['next_hook_ru'])

    def test_new_practice_is_reachable_and_remains_reachable_in_expanded_catalog(self):
        self.assertEqual(set(active_topics()),set(range(1,29)))
        for number,slug in ((23,'a1-dont-doesnt'),(24,'a1-letters-address')):
            practice=self.client.get(f'/lab/a1/{number}/?mission=6')
            self.assertEqual(practice.status_code,200)
            self.assertContains(practice,'data-start-mission="6"')
            lesson=self.client.get(f'/lessons/{slug}/')
            self.assertContains(lesson,f'/lab/a1/{number}/?mission=6')
        self.assertEqual(self.client.get('/lab/a1/29/').status_code,404)
