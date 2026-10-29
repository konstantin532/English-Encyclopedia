"""Week 2 finishes the planned A1 vocabulary inventory without new weeks."""
from django.test import TestCase
from apps.lexicon.models import LexicalUnit
from apps.lessons.models import Lesson
from apps.curriculum.models import WeekScene
from tests.runner import ensure_content

class WeekTwoExpansionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_completed_inventory_and_weekly_home_vocabulary(self):
        self.assertEqual(LexicalUnit.objects.filter(internal_level__code='A1').count(), 516)
        self.assertEqual(LexicalUnit.objects.filter(internal_level__code='A1', week__number=2).count(), 39)
        for n in range(1, 15):
            count = LexicalUnit.objects.filter(internal_level__code='A1', week__number=n).count()
            self.assertTrue(30 <= count <= 39, (n, count))

    def test_new_room_words_are_taught_in_dialogue_and_lessons(self):
        scene = WeekScene.objects.get(week__level__code='A1', week__number=2)
        text = ' '.join(line['text'] for line in scene.script)
        for word in ('kitchen', 'table', 'chair'):
            self.assertIn('[S2]' + word + '[/]', text)
        self.assertIn('Not My Box', scene.story_beat['next_hook_ru'])
        for lesson in Lesson.objects.filter(level__code='A1', order__in=(3, 4)):
            self.assertEqual(lesson.exercises.count(), 6)
            self.assertEqual(self.client.get('/lessons/' + lesson.slug + '/').status_code, 200)

    def test_new_entries_have_unique_lemmas_and_pending_verification(self):
        new = LexicalUnit.objects.filter(uid__gte='LX-00481', uid__lte='LX-00500')
        self.assertEqual(new.count(), 20)
        self.assertEqual(len(set(new.values_list('lemma', flat=True))), 20)
        for entry in new:
            self.assertEqual(entry.cefr, 'unverified')
