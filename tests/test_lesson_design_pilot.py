"""The visual trial is limited to two lessons and preserves their teaching material."""
from django.test import TestCase
from django.template import Context, Template
from django.urls import reverse

from apps.lessons.models import Lesson
from tests.runner import ensure_content


class LessonDesignPilotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_only_the_two_requested_lessons_receive_the_pilot(self):
        pilot_slugs = {"a1-nouns-first-words", "a1-verb-be"}
        lessons = Lesson.objects.filter(level__code__in=["A1", "A1+"], is_published=True)
        self.assertEqual(lessons.count(), 60)
        for lesson in lessons:
            with self.subTest(slug=lesson.slug):
                response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
                self.assertEqual(response.status_code, 200)
                if lesson.slug in pilot_slugs:
                    self.assertContains(response, "css/lesson-design-pilot.css")
                    self.assertContains(response, 'data-lesson-design-pilot')
                else:
                    self.assertNotContains(response, "css/lesson-design-pilot.css")
                    self.assertNotContains(response, 'data-lesson-design-pilot')

    def test_pilot_keeps_every_original_layer_and_exercise(self):
        for slug in ("a1-nouns-first-words", "a1-verb-be"):
            lesson = Lesson.objects.get(slug=slug)
            response = self.client.get(reverse("lessons:detail", args=[slug]))
            self.assertEqual(lesson.layers.count(), 7)
            for layer in lesson.layers.all():
                self.assertContains(response, f'id="layer-{layer.number}"')
                rendered = Template("{% load markers %}{{ body|annotate_block:True }}").render(Context({"body": layer.body}))
                self.assertContains(response, rendered, html=True)
            for exercise in lesson.exercises.all():
                self.assertContains(response, f'id="q{exercise.pk}"')
            for item in lesson.practice_items.all():
                self.assertContains(response, f'id="t{item.pk}"')
            self.assertContains(response, 'data-speech-persist="false"')
            self.assertContains(response, 'id="spoken-coach"')
