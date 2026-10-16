"""Проверки экспериментального урока: маршруты, безопасность методов и изоляция."""
from django.test import TestCase
from django.urls import reverse


class CafeLabTests(TestCase):
    def test_lab_is_accessible_to_guest(self):
        url = reverse("core:cafe_lab")
        self.assertEqual(url, "/lab/cafe/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/cafe_lab.html")
        self.assertContains(response, "Мия не расслышала заказ")
        self.assertContains(response, 'data-cafe-lab')
        self.assertContains(response, 'data-built-sentence')
        self.assertContains(response, 'data-listen-check')
        self.assertContains(response, 'data-free-answer')
        self.assertContains(response, 'data-recorder')
        self.assertContains(response, 'data-transfer-answer')

    def test_lab_has_six_accessible_steps(self):
        response = self.client.get(reverse("core:cafe_lab"))
        for target in (
            'id="cafe-listen"', 'id="cafe-meaning"', 'id="cafe-change"',
            'id="cafe-check"', 'id="cafe-speak"', 'id="cafe-transfer"',
        ):
            self.assertContains(response, target)
        self.assertContains(response, 'aria-live="polite"')

    def test_lab_is_read_only(self):
        response = self.client.post(reverse("core:cafe_lab"), {"answer": "b"})
        self.assertEqual(response.status_code, 405)

    def test_main_course_has_link_to_lab(self):
        response = self.client.get(reverse("lessons:detail", kwargs={"slug": "a1-cafe-order"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("core:cafe_lab"))

    def test_unrelated_lesson_does_not_show_lab_link(self):
        response = self.client.get(reverse("lessons:detail", kwargs={"slug": "a1-nouns-first-words"}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="cafe-lab-invite"')
