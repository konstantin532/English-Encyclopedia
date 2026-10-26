"""A1 always presents complete explanations without changing practice answers."""
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape
from apps.lessons.models import Lesson
from tests.runner import ensure_content


class A1LearningRouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_all_28_a1_lessons_show_every_original_layer_without_depth_menu(self):
        lessons = Lesson.objects.filter(level__code="A1", is_published=True)
        self.assertEqual(lessons.count(), 28)
        for lesson in lessons:
            with self.subTest(slug=lesson.slug):
                response = self.client.get(f"/lessons/{lesson.slug}/")
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "data-a1-full-lesson")
                self.assertNotContains(response, "data-a1-route-mode")
                self.assertNotContains(response, "data-a1-learning-route")
                self.assertNotContains(response, "data-route-availability")
                self.assertContains(response, "css/a1-lesson-reading.css")
                for layer in lesson.layers.all():
                    self.assertContains(response, f'id="layer-{layer.number}"', count=1)
                    self.assertContains(response, f'href="#layer-{layer.number}"', count=1)
                    annotated = Template("{% load markers %}{{ body|annotate_block }}").render(Context({"body": layer.body}))
                    self.assertContains(response, annotated, html=True)
                self.assertContains(response, 'id="practice"')
                self.assertContains(response, 'id="spoken-coach"')

    def test_brief_and_detailed_explanations_remain_once_in_all_a1_lessons(self):
        for lesson in Lesson.objects.filter(level__code="A1", is_published=True):
            with self.subTest(slug=lesson.slug):
                response = self.client.get(f"/lessons/{lesson.slug}/")
                self.assertContains(response, 'id="a1-clarity-title"', count=1)
                self.assertContains(response, 'id="beginner-steps"', count=1)
                self.assertContains(response, 'class="a1-step-en"', count=3)
                guide = response.context["a1_guide"]
                self.assertContains(response, escape(guide["plain"]))
                self.assertContains(response, escape(guide["why"]))

    def test_all_32_a1plus_lessons_keep_existing_structure_without_new_bridge(self):
        lessons = Lesson.objects.filter(level__code="A1+", is_published=True)
        self.assertEqual(lessons.count(), 32)
        for lesson in lessons:
            with self.subTest(slug=lesson.slug):
                response = self.client.get(f"/lessons/{lesson.slug}/")
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "data-a1-full-lesson")
                self.assertNotContains(response, 'id="a1-clarity-title"')
                self.assertNotContains(response, "css/a1-lesson-reading.css")
                for layer in lesson.layers.all():
                    self.assertContains(response, f'id="layer-{layer.number}"')

    def test_bookpage_presentation_is_only_loaded_for_the_noun_pilot(self):
        for order in (1, 2, 4, 28):
            with self.subTest(order=order):
                lesson = Lesson.objects.get(level__code="A1", order=order)
                response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
                if order == 1:
                    self.assertContains(response, 'data-lesson-bookpage')
                    self.assertContains(response, 'css/lesson-bookpage.css')
                else:
                    self.assertNotContains(response, 'data-lesson-bookpage')
                    self.assertNotContains(response, 'css/lesson-bookpage.css')

    def test_bookpage_preserves_every_annotated_explanation(self):
        from apps.taxonomy.templatetags.markers import annotate_block

        lesson = Lesson.objects.get(slug="a1-nouns-first-words")
        response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
        for layer in lesson.layers.all():
            with self.subTest(layer=layer.number):
                self.assertContains(response, annotate_block(layer.body))
        self.assertContains(response, lesson.title)
        self.assertContains(response, lesson.summary)
        self.assertContains(response, 'class="aside"')
        self.assertContains(response, 'data-reader-larger')
        self.assertContains(response, 'data-speech-studio')
