"""Week 13: classroom vocabulary and ability/reason practice."""
from django.test import TestCase
from apps.core.a1_active import active_topics
from apps.curriculum.models import WeekScene
from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit
from tests.runner import ensure_content


class WeekThirteenExpansionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_classroom_and_skill_vocabulary_is_taught(self):
        expected = {'learn', 'study', 'repeat', 'understand', 'draw', 'swim', 'drive',
                    'dance', 'classroom', 'course', 'lesson', 'homework', 'notebook',
                    'pencil', 'pen', 'page', 'sentence', 'question', 'exercise', 'test',
                    'language', 'easy', 'difficult'}
        week = LexicalUnit.objects.filter(internal_level__code='A1', week__number=13)
        self.assertEqual(week.count(), 36)
        self.assertTrue(expected <= set(week.values_list('lemma', flat=True)))
        for lesson in Lesson.objects.filter(level__code='A1', order__in=(25, 26)):
            self.assertEqual(list(lesson.exercises.order_by('order').values_list('order', flat=True)), [1, 2, 3, 4, 5, 6])

    def test_dialogue_preserves_canonical_lesson_time_and_motives(self):
        scene = WeekScene.objects.get(week__level__code='A1', week__number=13)
        text = ' '.join(line['text'] for line in scene.script)
        for marked in ('[D6]learn[/]', '[S9]lesson[/]', '[S2]notebook[/]'):
            self.assertIn(marked, text)
        self.assertIn('[S7]Saturday[/] [P3]at[/] [N3]ten[/]', text)
        self.assertIn('[S10]Russian[/] [S10]music[/]', text)
        self.assertIn('[S10]Russian[/] [S9]letters[/]', text)
        self.assertIn('шкаф', scene.story_beat['next_hook_ru'])

    def test_new_practice_is_reachable_and_remains_reachable_in_full_a1_catalog(self):
        self.assertEqual(set(active_topics()), set(range(1, 29)))
        for number, slug in ((25, 'a1-can-skills'), (26, 'a1-why-because')):
            practice = self.client.get(f'/lab/a1/{number}/?mission=6')
            self.assertEqual(practice.status_code, 200)
            self.assertContains(practice, 'data-start-mission="6"')
            self.assertContains(self.client.get(f'/lessons/{slug}/'), f'/lab/a1/{number}/?mission=6')
        self.assertEqual(self.client.get('/lab/a1/29/').status_code, 404)
