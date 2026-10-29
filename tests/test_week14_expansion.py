"""Week 14: travel vocabulary and full A1 supplemental catalog."""
from django.test import TestCase
from apps.core.a1_active import active_topics
from apps.curriculum.models import WeekScene
from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit
from tests.runner import ensure_content


class WeekFourteenExpansionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_travel_weather_and_clothing_words_are_taught(self):
        expected = {"weather","sunny","rain","snow","windy","cloudy","warm","train","car","taxi","station","airport","plane","trip","travel","arrive","leave","buy","coat","hat","umbrella","bag","sweater","seat"}
        week = LexicalUnit.objects.filter(internal_level__code='A1', week__number=14)
        self.assertEqual(week.count(), 36)
        self.assertTrue(expected <= set(week.values_list('lemma', flat=True)))
        for lesson in Lesson.objects.filter(level__code='A1', order__in=(27, 28)):
            self.assertEqual(list(lesson.exercises.order_by('order').values_list('order', flat=True)), [1, 2, 3, 4, 5, 6])

    def test_dialogue_preserves_bus_fare_time_and_photo_shop_hook(self):
        scene = WeekScene.objects.get(week__level__code='A1', week__number=14)
        text = ' '.join(line['text'] for line in scene.script)
        for marked in ('[S4]train[/]', '[S4]station[/]', '[S2]seat[/]'):
            self.assertIn(marked, text)
        self.assertIn('[N6]two dollars[/]', text)
        self.assertIn('[P3]at[/] [N3]six[/]', text)
        self.assertIn('[S2]photo[/] [S4]shop[/]', text)
        self.assertIn('Open Monday', scene.story_beat['next_hook_ru'])

    def test_new_practice_is_reachable_and_stops_before_twenty_nine(self):
        self.assertEqual(set(active_topics()), set(range(1, 29)))
        for number, slug in ((27, 'a1-bus-ticket'), (28, 'a1-review-everything')):
            practice = self.client.get(f'/lab/a1/{number}/?mission=6')
            self.assertEqual(practice.status_code, 200)
            self.assertContains(practice, 'data-start-mission="6"')
            self.assertContains(self.client.get(f'/lessons/{slug}/'), f'/lab/a1/{number}/?mission=6')
        self.assertContains(self.client.get('/lab/a1/28/'), 'Все 28 тем дополнительной практики A1 доступны.')
        self.assertEqual(self.client.get('/lab/a1/29/').status_code, 404)
