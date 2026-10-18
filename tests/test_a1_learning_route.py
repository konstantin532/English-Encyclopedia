"""The optional A1 pilot must preserve all original lesson content and controls."""
from django.test import TestCase
from django.urls import reverse

from apps.lessons.models import Lesson
from tests.runner import ensure_content


class A1LearningRouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_first_four_lessons_keep_seven_layers_and_full_practice(self):
        for order in range(1, 5):
            with self.subTest(order=order):
                lesson = Lesson.objects.get(level__code="A1", order=order)
                response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-a1-learning-route')
                self.assertContains(response, 'data-a1-route-mode="essentials"')
                self.assertContains(response, 'data-a1-route-mode="reasons"')
                self.assertContains(response, 'data-a1-route-mode="full"')
                self.assertContains(response, 'data-a1-route-mode="full" aria-pressed="true"')
                self.assertContains(response, 'data-lesson-reader')
                self.assertContains(response, 'js/a1-learning-route.js')
                for n in range(1, 8):
                    self.assertContains(response, f'id="layer-{n}"')
                    self.assertEqual(lesson.layers.get(number=n).number, n)
                self.assertContains(response, 'id="practice"')
                self.assertContains(response, "data-lesson-practice")
                self.assertContains(response, 'id="spoken-coach"')
                self.assertContains(response, 'class="section a1-active-invite"')

    def test_reading_depths_extend_to_all_28_a1_lessons(self):
        for order in range(5, 29):
            with self.subTest(order=order):
                lesson = Lesson.objects.get(level__code="A1", order=order)
                response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-a1-learning-route')
                self.assertContains(response, 'js/a1-learning-route.js')
                self.assertContains(response, 'id="layer-7"')
                self.assertContains(response, 'id="practice"')
                self.assertContains(response, 'class="a1-step-list"')
                self.assertContains(response, 'class="a1-step-en"', count=3)
