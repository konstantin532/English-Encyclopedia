"""Regression and content-integrity checks for the A1 01–18 add-on.

The situation-weeks curriculum and database schema must stay unchanged.
"""
import json
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.core.a1_active import MAX_TOPIC, TOPIC_FILES, active_topics
from apps.lessons.models import Lesson
from tests.runner import ensure_content


class ActiveA1CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_has_exactly_eighteen_distinct_topics_and_valid_order(self):
        topics = active_topics()
        self.assertEqual(MAX_TOPIC, 18)
        self.assertEqual(sorted(topics), list(range(1, 19)))
        slugs = [item["slug"] for item in topics.values()]
        self.assertEqual(len(slugs), len(set(slugs)))
        for index, topic in topics.items():
            self.assertEqual(topic["n"], index)
            self.assertEqual(topic["week"], (index + 1) // 2)
            lesson = Lesson.objects.get(slug=topic["slug"])
            self.assertEqual(lesson.order, index)
            self.assertEqual(lesson.level.code, "A1")
            self.assertEqual(lesson.week.number, topic["week"])

    def test_content_meets_five_step_minimum(self):
        for index, topic in active_topics().items():
            with self.subTest(index=index):
                for key in ("title", "scene", "context", "question", "feedback", "prompt",
                            "answer", "hint", "transfer", "transfer_example", "why", "sound"):
                    self.assertIsInstance(topic[key], str)
                    self.assertGreater(len(topic[key].strip()), 4)
                self.assertGreaterEqual(len(topic["dialogue"]), 2)
                for line in topic["dialogue"]:
                    self.assertEqual(len(line), 3)
                    self.assertTrue(all(isinstance(s, str) and s.strip() for s in line))
                self.assertEqual(len(topic["options"]), 3)
                self.assertEqual(len(set(topic["options"])), 3)
                self.assertIsInstance(topic["correct"], int)
                self.assertIn(topic["correct"], range(3))
                self.assertIsInstance(topic["alternatives"], list)
                self.assertNotIn("<script", json.dumps(topic).lower())

    def test_catalog_source_files_are_bounded_and_present(self):
        self.assertEqual(TOPIC_FILES, ("topics_01_08.json", "topics_09_13.json", "topics_14_18.json"))
        root = Path(settings.BASE_DIR) / "content" / "active_a1"
        self.assertEqual(sum(len(json.loads((root / f).read_text(encoding="utf-8"))) for f in TOPIC_FILES), 18)
        self.assertFalse((root / "topics_19_22.json").exists())

    def test_every_topic_is_accessible_by_get(self):
        for n in range(1, 19):
            with self.subTest(n=n):
                response = self.client.get(reverse("core:active_a1_topic", args=[n]))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "core/a1_active_topic.html")
                self.assertContains(response, f"Тема {n} из 18")
                self.assertContains(response, "data-a1-quiz")
                self.assertContains(response, "data-a1-production")
                self.assertContains(response, "data-a1-builder")
                self.assertContains(response, "data-a1-builder-check")
                self.assertContains(response, "data-a1-builder-undo")
                self.assertContains(response, "data-a1-transfer")
                self.assertContains(response, 'id="a1-active-topic-data"')

    def test_out_of_range_topic_is_404(self):
        for n in (0, 19, 22, 99999):
            self.assertEqual(self.client.get(reverse("core:active_a1_topic", args=[n])).status_code, 404)

    def test_no_server_side_submission_or_private_audio(self):
        response = self.client.post(reverse("core:active_a1_topic", args=[18]), {"answer": "Tom"})
        self.assertEqual(response.status_code, 405)
        response = self.client.get(reverse("core:active_a1_topic", args=[18]))
        self.assertNotContains(response, "getUserMedia")
        self.assertNotContains(response, "MediaRecorder")

    def test_links_on_existing_lessons_are_bounded(self):
        for n in (1, 5, 9, 14, 18):
            lesson = Lesson.objects.get(level__code="A1", order=n)
            response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
            self.assertContains(response, reverse("core:active_a1_topic", args=[n]))
        for n in (19, 22, 28):
            lesson = Lesson.objects.get(level__code="A1", order=n)
            response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
            self.assertNotContains(response, 'class="section a1-active-invite"')

    def test_new_material_does_not_replace_original_cafe_lab(self):
        response = self.client.get(reverse("lessons:detail", args=["a1-cafe-order"]))
        self.assertContains(response, reverse("core:cafe_lab"))
        self.assertContains(response, reverse("core:active_a1_topic", args=[5]))

    def test_unpublished_lesson_hides_its_supplemental_page(self):
        lesson = Lesson.objects.get(level__code="A1", order=18)
        lesson.is_published = False
        lesson.save(update_fields=["is_published"])
        response = self.client.get(reverse("core:active_a1_topic", args=[18]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.client.get(reverse("core:active_a1_topic", args=[17])).status_code, 200
        )

    def test_deleted_source_slug_does_not_show_stale_practice(self):
        lesson = Lesson.objects.get(level__code="A1", order=18)
        lesson.slug = "renamed-a1-spelling"
        lesson.save(update_fields=["slug"])
        self.assertEqual(self.client.get(reverse("core:active_a1_topic", args=[18])).status_code, 404)

    def test_builder_is_hidden_before_first_independent_response(self):
        response = self.client.get(reverse("core:active_a1_topic", args=[18]))
        self.assertContains(response, 'class="active-a1-builder" data-a1-builder hidden')
        self.assertContains(response, 'data-a1-model hidden')
        self.assertContains(response, 'data-a1-transfer-feedback hidden')
