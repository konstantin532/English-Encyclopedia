"""Regression and content-integrity checks for the A1 01–20 add-on.

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

    def test_has_exactly_twenty_distinct_topics_and_valid_order(self):
        topics = active_topics()
        self.assertEqual(MAX_TOPIC, 20)
        self.assertEqual(sorted(topics), list(range(1, 21)))
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
        self.assertEqual(TOPIC_FILES, ("topics_01_08.json", "topics_09_13.json", "topics_14_18.json", "topics_19_20.json"))
        root = Path(settings.BASE_DIR) / "content" / "active_a1"
        self.assertEqual(sum(len(json.loads((root / f).read_text(encoding="utf-8"))) for f in TOPIC_FILES), 20)
        self.assertTrue((root / "topics_19_20.json").exists())
        self.assertFalse((root / "topics_21_22.json").exists())

    def test_every_topic_is_accessible_by_get(self):
        for n in range(1, 21):
            with self.subTest(n=n):
                response = self.client.get(reverse("core:active_a1_topic", args=[n]))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "core/a1_active_topic.html")
                self.assertContains(response, f"Тема {n} из 20")
                self.assertContains(response, "data-a1-quiz")
                self.assertContains(response, "data-a1-production")
                self.assertContains(response, "data-a1-builder")
                self.assertContains(response, "data-a1-builder-check")
                self.assertContains(response, "data-a1-builder-undo")
                self.assertContains(response, "data-a1-repair-form")
                self.assertContains(response, "data-a1-repair-reveal")
                self.assertContains(response, "data-a1-transfer")
                self.assertContains(response, 'id="a1-active-topic-data"')

    def test_out_of_range_topic_is_404(self):
        for n in (0, 21, 22, 99999):
            self.assertEqual(self.client.get(reverse("core:active_a1_topic", args=[n])).status_code, 404)

    def test_no_server_side_submission_or_private_audio(self):
        response = self.client.post(reverse("core:active_a1_topic", args=[18]), {"answer": "Tom"})
        self.assertEqual(response.status_code, 405)
        response = self.client.get(reverse("core:active_a1_topic", args=[18]))
        self.assertNotContains(response, "getUserMedia")
        self.assertNotContains(response, "MediaRecorder")

    def test_links_on_existing_lessons_are_bounded(self):
        for n in (1, 5, 9, 14, 18, 19, 20):
            lesson = Lesson.objects.get(level__code="A1", order=n)
            response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
            self.assertContains(response, reverse("core:active_a1_topic", args=[n]))
        for n in (21, 22, 28):
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
        self.assertContains(response, 'class="active-a1-repair" data-a1-repair hidden')
        self.assertContains(response, 'data-a1-repair-explanation role="status" aria-live="polite" hidden')

    def test_all_twenty_error_repairs_are_original_and_present(self):
        from apps.core.a1_active import active_topics
        from django.utils.html import escape
        for i, topic in active_topics().items():
            with self.subTest(i=i):
                repair = topic["repair"]
                for field in ("wrong", "correct", "hint", "reason"):
                    self.assertIsInstance(repair[field], str)
                    self.assertGreater(len(repair[field]), 8 if field != "hint" else 4)
                self.assertNotEqual(repair["wrong"], repair["correct"])
                response = self.client.get(reverse("core:active_a1_topic", args=[i]))
                self.assertContains(response, escape(repair["wrong"]))
                self.assertContains(response, escape(repair["correct"]))

    def test_six_new_scenarios_per_lesson_and_two_improv_twists(self):
        topics = active_topics()
        self.assertEqual(sum(len(topic["missions"]) for topic in topics.values()), 120)
        self.assertEqual(sum(len(topic["twists"]) for topic in topics.values()), 40)
        titles = []
        scenes = []
        for number, topic in topics.items():
            with self.subTest(number=number):
                missions = topic["missions"]
                self.assertEqual([m["id"] for m in missions], [1, 2, 3, 4, 5, 6])
                self.assertEqual(len(topic["twists"]), 2)
                self.assertEqual(len({m["title"] for m in missions}), 6)
                self.assertEqual(len({m["scene"] for m in missions}), 6)
                for mission in missions:
                    for field in ("title", "scene", "prompt", "example", "coach"):
                        self.assertIsInstance(mission[field], str)
                        self.assertGreaterEqual(
                            len(mission[field].strip()), 1 if field == "example" else 5
                        )
                    self.assertLessEqual(len(mission["example"]), 200)
                    titles.append(mission["title"])
                    scenes.append(mission["scene"])
                for twist in topic["twists"]:
                    self.assertTrue(twist["scene"] and twist["example"])
                    self.assertLessEqual(len(twist["example"]), 200)
        self.assertEqual(len(set(titles)), 120)
        self.assertEqual(len(set(scenes)), 120)

    def test_missions_render_on_every_topic_page_without_exposing_models(self):
        for number in range(1, 21):
            with self.subTest(number=number):
                response = self.client.get(reverse("core:active_a1_topic", args=[number]))
                self.assertContains(response, 'id="a1-missions"')
                self.assertContains(response, 'data-a1-mission-form')
                self.assertContains(response, 'data-a1-mission-progress')
                self.assertContains(response, 'data-a1-mission-twist')
                self.assertContains(response, 'data-a1-mission-result')
                self.assertContains(response, 'data-a1-mission-speak')
                self.assertContains(response, 'data-a1-mission-result class="active-a1-feedback')
                self.assertContains(response, 'data-a1-mission-result class="active-a1-feedback active-a1-mission-result" aria-live="polite" role="status" hidden')
                self.assertContains(response, 'data-a1-mission-twist-controls class="active-a1-mission-twist-controls" hidden')
                self.assertContains(response, 'data-a1-mission-index="5"')
                self.assertNotContains(response, 'data-a1-mission-index="6"')

    def test_existing_lesson_and_mission_are_both_linked(self):
        response = self.client.get(reverse("lessons:detail", args=["a1-spelling-phone-numbers"]))
        self.assertContains(response, reverse("core:active_a1_topic", args=[18]))
        self.assertContains(response, reverse("core:active_a1_topic", args=[18]) + "#a1-missions")

    def test_six_story_cards_are_visible_below_the_canonical_lesson(self):
        for number in (1, 5, 13, 18, 19, 20):
            with self.subTest(lesson=number):
                lesson = Lesson.objects.get(level__code="A1", order=number)
                response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
                self.assertContains(response, 'class="a1-mission-previews"')
                self.assertEqual(response.content.decode("utf-8").count('aria-label="Попробовать ситуацию'), 6)
                self.assertContains(
                    response, reverse("core:active_a1_topic", args=[number]) + "?mission=6#"
                )
        lesson = Lesson.objects.get(level__code="A1", order=21)
        response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
        self.assertNotContains(response, 'class="a1-mission-previews"')

    def test_source_lesson_deep_links_select_only_valid_mission_numbers(self):
        url = reverse("core:active_a1_topic", args=[18])
        for value, expected in (("3", 3), ("6", 6), ("0", 1),
                                ("7", 1), ("abc", 1), ("-5", 1)):
            with self.subTest(value=value):
                response = self.client.get(url, {"mission": value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["start_mission"], expected)
                self.assertContains(response, f'data-start-mission="{expected}"')

    def test_new_topics_train_week_ten_and_accept_the_infinitive_alternative(self):
        topics = active_topics()
        self.assertEqual(topics[19]["slug"], "a1-always-never")
        self.assertEqual(topics[20]["slug"], "a1-like-doing")
        self.assertEqual(topics[19]["week"], 10)
        self.assertEqual(topics[20]["week"], 10)
        self.assertIn("I like to read.", topics[20]["alternatives"])
        self.assertIn("I like to read.", topics[20]["repair"]["alternatives"])
        last = self.client.get(reverse("core:active_a1_topic", args=[20]))
        self.assertIsNone(last.context["topic_next"])
        self.assertEqual(last.context["topic_previous"], 19)
