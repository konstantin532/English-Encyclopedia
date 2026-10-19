"""Focused first-pass regressions: pagination, editorial semantics and accessible tasks."""
from pathlib import Path

from django.conf import settings
from django.test import TestCase, SimpleTestCase
from django.urls import reverse

from tests.runner import ensure_content


class DictionaryPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_dictionary_page_is_bounded_and_has_navigation(self):
        response = self.client.get(reverse("lexicon:list"))
        self.assertEqual(response.status_code, 200)
        page = response.context["page_obj"]
        self.assertEqual(len(page.object_list), 48)
        self.assertGreater(response.context["total_units"], 48)
        self.assertContains(response, 'rel="next"')
        self.assertContains(response, 'aria-label="Страницы словаря"')

    def test_large_json_payload_is_rejected_before_parsing(self):
        from django.test import RequestFactory
        from apps.api.validation import read_answer_payload
        request = RequestFactory().post(
            "/api/units/test/recall/",
            data='{"answer":"ok","filler":"' + "x" * 17000 + '"}',
            content_type="application/json",
        )
        with self.assertRaisesMessage(ValueError, "Слишком большой запрос"):
            read_answer_payload(request)

    def test_dictionary_page_out_of_range_and_filter_state(self):
        response = self.client.get(reverse("lexicon:list"), {"page": "999999", "level": "A1", "q": "a"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, response.context["page_obj"].paginator.num_pages)
        if response.context["page_obj"].has_previous():
            self.assertContains(response, "level=A1")
            self.assertContains(response, "q=a")
        self.assertNotContains(response, "page=999999")


class AccessibilityEditorialContracts(SimpleTestCase):
    def test_poem_stress_is_not_misnamed_syllabic_stress(self):
        markup = (Path(settings.BASE_DIR) / "templates/poems/detail.html").read_text("utf-8")
        self.assertIn("смысловое ударение на слове", markup)
        self.assertNotIn("Заглавные буквы — ударный слог", markup)
        self.assertIn("в строке {{ forloop.counter }}", markup)

    def test_story_phrase_controls_have_target_ids(self):
        markup = (Path(settings.BASE_DIR) / "templates/stories/detail.html").read_text("utf-8")
        self.assertIn('aria-controls="hunt-function-{{ forloop.counter }}"', markup)
        script = (Path(settings.BASE_DIR) / "static/js/story-player.js").read_text("utf-8")
        self.assertIn('other.setAttribute("aria-expanded", "false")', script)
