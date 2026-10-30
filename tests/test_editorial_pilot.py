"""The editorial trial changes two reading pages without changing course data."""
from django.test import TestCase
from django.template.loader import render_to_string
from django.urls import reverse
from django.test.html import parse_html
from apps.lessons.models import Lesson
from tests.runner import ensure_content


class EditorialPilotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_pilot_is_limited_to_requested_week_and_lesson(self):
        from apps.accounts.models import User
        self.client.force_login(User.objects.create_user("pilot-student@example.test"))
        for url, enabled in [("/levels/a1/weeks/3/", True), ("/lessons/a1-cafe-order/", True), ("/levels/a1/weeks/2/", False), ("/levels/a1/weeks/4/", False), ("/lessons/a1-nouns-first-words/", False), ("/stories/1/", False), ("/levels/a1/", False), ("/", False)]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(b"data-editorial-pilot" in response.content, enabled)

    def test_week_chapter_image_precedes_title_and_has_dimensions(self):
        html = self.client.get("/levels/a1/weeks/3/").content.decode()
        self.assertIn('class="editorial-chapter-art"', html)
        self.assertLess(html.index('class="editorial-chapter-art"'), html.index("<h1"))
        self.assertIn('width="1536" height="864"', html)
        self.assertIn("Ваш маршрут", html)

    def test_glossary_has_every_unit_translation_ipa_and_link(self):
        lesson = Lesson.objects.get(slug="a1-cafe-order")
        response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
        self.assertContains(response, 'class="editorial-glossary')
        for unit in lesson.units.all():
            self.assertContains(response, reverse("lexicon:detail", args=[unit.uid]))
            self.assertContains(response, unit.translation_ru)
            if unit.ipa_us:
                self.assertContains(response, unit.ipa_us)
        self.assertContains(response, "Фразы")

    def test_all_original_lesson_layers_and_exercises_remain(self):
        lesson = Lesson.objects.get(slug="a1-cafe-order")
        response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
        for layer in lesson.layers.all():
            self.assertContains(response, f'id="layer-{layer.number}"')
        for exercise in lesson.exercises.all():
            self.assertContains(response, f'id="q{exercise.pk}"')
        for item in lesson.practice_items.all():
            self.assertContains(response, f'id="t{item.pk}"')
        self.assertContains(response, 'id="lesson-extra-practice"')

    def test_sidenote_preserves_text_with_javascript_unavailable_and_escapes_html(self):
        html = render_to_string("components/editorial_sidenote.html", {"note_title": "Почему так?", "note_text": "<script>alert(1)</script>"})
        self.assertIn("<details", html)
        self.assertIn(" open", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)

    def test_margin_note_is_outside_the_audio_activation_control(self):
        html = render_to_string("components/editorial_dialogue_line.html", {"l": {
            "i": 0, "kind": "speech", "speaker": "tom", "name": "Том",
            "text": "I would like tea.", "spoken": "I'd like tea.", "ru": "Я хотел бы чай.",
        }})
        def elements(node):
            yield node
            for child in getattr(node, "children", []):
                if not isinstance(child, str):
                    yield from elements(child)
        nodes = list(elements(parse_html(html)))
        line = next(node for node in nodes if "data-line" in dict(getattr(node, "attributes", [])))
        self.assertNotIn("details", [node.name for node in elements(line)])
        self.assertIn("details", [node.name for node in nodes])
