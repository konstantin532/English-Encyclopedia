"""Published A1 stories must fit the course's beginner reading budget.

This checks the loaded learner text, not comprehension or audio quality.
"""
from django.test import TestCase

from apps.publishing.audit import text_tokens
from apps.stories.models import Story
from tests.runner import ensure_content


class A1StoryReadingLoadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_published_a1_stories_fit_sixty_to_eighty_words(self):
        stories = Story.objects.filter(level__code="A1", is_published=True)
        self.assertEqual(stories.count(), 5)
        for story in stories:
            with self.subTest(story=story.number):
                count = len(text_tokens(story.body))
                self.assertGreaterEqual(count, 60)
                self.assertLessEqual(count, 80)
