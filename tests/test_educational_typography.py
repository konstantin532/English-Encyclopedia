"""Typography may change presentation, never the source teaching material."""
from django.template import Context, Template
from django.test import TestCase

from apps.curriculum.models import Week
from django.utils.html import escape
from apps.lessons.models import Lesson
from apps.stories.models import Story
from apps.poems.models import Poem
from tests.runner import ensure_content


def annotated(value, block=False, plain_labels=False):
    filter_name = "annotate_block:plain_labels" if block else "annotate"
    return Template("{% load markers %}{{ value|" + filter_name + " }}").render(Context({"value": value, "plain_labels": plain_labels}))


class EducationalTypographyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def assert_reading_surface(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-educational-reading')
        self.assertContains(response, 'css/educational-reading.css')

    def test_every_published_lesson_keeps_all_annotated_layers(self):
        lessons = Lesson.objects.filter(is_published=True)
        self.assertEqual(lessons.count(), 60)
        for lesson in lessons:
            with self.subTest(slug=lesson.slug):
                response = self.client.get(f"/lessons/{lesson.slug}/")
                self.assert_reading_surface(response)
                for layer in lesson.layers.all():
                    self.assertContains(response, annotated(layer.body, block=True, plain_labels=lesson.level.code == "A1"))
                self.assertContains(response, 'data-lesson-design-pilot', count=1 if lesson.slug in {"a1-nouns-first-words", "a1-verb-be"} else 0)

    def test_stories_keep_each_speaker_and_both_forms(self):
        stories = Story.objects.filter(is_published=True)
        self.assertEqual(stories.count(), 11)
        for story in stories:
            response = self.client.get(f"/stories/{story.number}/")
            self.assert_reading_surface(response)
            for line in response.context["lines"]:
                self.assertContains(response, f'data-speaker="{line["speaker"]}"')
                self.assertContains(response, annotated(line["text"]))
                if line.get("spoken"):
                    self.assertContains(response, annotated(line["spoken"]))

    def test_poems_keep_lines_stanzas_and_ipa(self):
        poems = Poem.objects.filter(is_published=True)
        self.assertEqual(poems.count(), 7)
        for poem in poems:
            response = self.client.get(f"/stories/poems/{poem.number}/")
            self.assert_reading_surface(response)
            for row in response.context["rows"]:
                self.assertContains(response, annotated(row["line"]))
                if row.get("pr"):
                    self.assertContains(response, row["pr"]["ipa"])
            stanzas = sum(bool(row.get("stanza")) for row in response.context["rows"])
            self.assertContains(response, 'class="stanza-start"', count=stanzas * 2)

    def test_dialogues_keep_each_translation_and_role(self):
        weeks = Week.objects.filter(scene__isnull=False).select_related("level")
        self.assertEqual(weeks.count(), 30)
        for week in weeks:
            response = self.client.get(f"/levels/{week.level.slug}/weeks/{week.number}/")
            self.assert_reading_surface(response)
            for line in response.context["lines"]:
                self.assertContains(response, annotated(line["text"]))
                if line.get("ru"):
                    self.assertContains(response, escape(line["ru"]))
                self.assertContains(response, f'data-speaker="{line["speaker"]}"')

    def test_non_learning_pages_have_no_reading_theme(self):
        for url in ("/", "/levels/a1/", "/accounts/login/"):
            response = self.client.get(url)
            self.assertNotContains(response, 'data-educational-reading')
            self.assertNotContains(response, 'css/educational-reading.css')
