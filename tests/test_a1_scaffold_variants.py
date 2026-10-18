"""Beginner editorial scaffolds, independently varied transfer, and honest reflection."""
import json
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.learning.models import IndependentAttempt, UnitProgress
from apps.learning.understanding import scaffold_bank, understanding_bank
from apps.lessons.models import Lesson
from tests.runner import ensure_content


class ThreeStepEditorialTests(SimpleTestCase):
    def test_each_a1_lesson_has_three_specific_steps_and_distinct_transfer(self):
        rows = scaffold_bank()
        self.assertEqual(len(rows), 28)
        self.assertEqual(sum(len(r["steps"]) for r in rows.values()), 84)
        guides = understanding_bank()
        self.assertEqual(set(rows), set(guides))
        for slug, guide in guides.items():
            with self.subTest(slug=slug):
                self.assertEqual(len(guide["steps"]), 3)
                self.assertEqual(len(guide["transfer_variants"]), 1)
                fresh = guide["transfer_variants"][0]
                self.assertNotEqual(
                    fresh["prompt"], guide["tasks"]["transfer"]["prompt"])
                self.assertNotIn("accepted", fresh)
                self.assertNotIn("options", fresh)
                self.assertNotEqual(fresh["prompt"], fresh["model"])
                self.assertGreaterEqual(
                    len({step["example_en"] for step in guide["steps"]}), 3)

    def test_micro_review_explanations_keep_relevant_true_rules(self):
        guides = understanding_bank()
        # Independent examples must not teach false bans on valid constructions.
        self.assertIn("like to read", " ".join(
            x["example_en"] for x in guides["a1-like-doing"]["steps"]))
        self.assertIn("Does he work", " ".join(
            x["example_en"] for x in guides["a1-he-she-works"]["steps"]))
        self.assertIn("There is some water", " ".join(
            x["example_en"] for x in guides["a1-there-is-some"]["steps"]))

    def test_phone_readability_and_accessibility_contracts(self):
        css = (Path(settings.BASE_DIR) / "static/css/independent-check.css").read_text("utf-8")
        for rule in ("max-width: 430px", "min-height: 52px",
                     "focus-visible", "forced-colors: active",
                     "prefers-reduced-motion: reduce",
                     "overflow-wrap: anywhere", "font-size: max(1rem, 16px)"):
            with self.subTest(rule=rule):
                self.assertIn(rule, css)


class RotatingIndependentReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.student = User.objects.create_user(
            email="new-transfer@example.test", password="LongTestPass123!")
        self.other = User.objects.create_user(
            email="new-transfer-other@example.test", password="LongTestPass123!")
        self.lesson = Lesson.objects.get(level__code="A1", order=13)
        self.url = reverse("learning:independent_check", args=[self.lesson.slug])
        self.client.force_login(self.student)

    def batch(self, variant=None):
        page = self.client.get(self.url)
        guide = page.context["guide"]
        current = page.context["transfer_variant"]
        answers = {"action": "batch",
                   **{"answer_" + key: guide["tasks"][key]["model"]
                      for key in ("meaning", "writing", "transfer", "explain")}}
        if variant is not None:
            answers["transfer_variant"] = str(variant)
        return self.client.post(self.url, answers)

    def test_all_28_lessons_render_three_steps(self):
        for lesson in Lesson.objects.filter(level__code="A1"):
            with self.subTest(lesson=lesson.order):
                response = self.client.get(
                    reverse("lessons:detail", args=[lesson.slug]))
                self.assertContains(response, 'class="a1-step-list"')
                self.assertContains(response, 'class="a1-step-en"', count=3)
                self.assertContains(response, "Разобрать ещё проще")
                self.assertContains(response, 'data-a1-learning-route')

    def test_baseline_then_fresh_transfer_are_rotated_only_after_full_batch(self):
        before = self.client.get(self.url)
        self.assertEqual(before.context["transfer_variant"], 0)
        baseline = before.context["guide"]["tasks"]["transfer"]["prompt"]
        self.assertEqual(before.context["transfer_variant_total"], 2)
        result = self.batch(variant=0)
        self.assertEqual(result.status_code, 200)
        self.assertContains(result, "Разбор всех четырёх ответов")
        saved = IndependentAttempt.objects.get(
            user=self.student, skill="transfer")
        self.assertEqual(saved.task_variant, 0)

        after = self.client.get(self.url)
        self.assertEqual(after.context["transfer_variant"], 1)
        self.assertNotEqual(after.context["guide"]["tasks"]["transfer"]["prompt"], baseline)
        self.assertEqual(
            self.client.post(self.url, {"action": "batch", "transfer_variant": "0"}).status_code,
            400)
        self.assertEqual(self.batch(variant=1).status_code, 200)
        self.assertEqual(IndependentAttempt.objects.filter(
            user=self.student, skill="transfer", task_variant=1).count(), 1)
        self.assertEqual(self.client.get(self.url).context["transfer_variant"], 0)
        self.assertFalse(UnitProgress.objects.filter(user=self.student).exists())

    def test_partial_batch_does_not_rotate_or_store_any_answers(self):
        result = self.client.post(self.url, {
            "action": "batch", "transfer_variant": "0", "answer_meaning": "Да",
            "answer_writing": "Hello", "answer_transfer": "",
            "answer_explain": "Понимаю правило"})
        self.assertEqual(result.status_code, 400)
        self.assertEqual(self.client.get(self.url).context["transfer_variant"], 0)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.student).exists())

    def test_four_axis_reflection_never_changes_cefr_or_vocabulary(self):
        self.assertEqual(self.batch(variant=0).status_code, 200)
        attempt = IndependentAttempt.objects.get(user=self.student, skill="transfer")
        page = self.client.get(self.url)
        self.assertContains(page, 'name="answer_transfer"')
        invalid = self.client.post(self.url, {
            "action": "rubric", "attempt_id": attempt.pk,
            "rubric_meaning": "yes", "rubric_form": "magical",
            "rubric_context": "yes", "rubric_independence": "independent"})
        self.assertEqual(invalid.status_code, 400)
        attempt.refresh_from_db()
        self.assertEqual(attempt.self_rubric, {})
        accepted = self.client.post(self.url, {
            "action": "rubric", "attempt_id": attempt.pk,
            "rubric_meaning": "yes", "rubric_form": "partly",
            "rubric_context": "yes", "rubric_independence": "helped"})
        self.assertEqual(accepted.status_code, 200)
        attempt.refresh_from_db()
        self.assertEqual(attempt.self_rubric,
                         {"meaning": "yes", "form": "partly",
                          "context": "yes", "independence": "helped"})
        self.assertEqual(attempt.self_rating, "helped")
        self.assertFalse(UnitProgress.objects.filter(user=self.student).exists())

    def test_rubric_has_accessible_radio_groups_and_does_not_leak_before_answer(self):
        initial = self.client.get(self.url)
        self.assertNotContains(initial, 'name="rubric_meaning"')
        self.assertNotContains(initial, "Один возможный образец")
        response = self.batch(variant=0)
        self.assertContains(response, 'name="rubric_meaning"', count=6)
        self.assertContains(response, 'name="rubric_form"', count=6)
        self.assertContains(response, 'name="rubric_context"', count=6)
        self.assertContains(response, 'name="rubric_independence"', count=6)
        self.assertContains(response, "Как у вас получилось?")
        self.assertContains(response, 'aria-describedby="skill-transfer"')
        self.assertContains(response, 'lang="en"')

    def test_cross_user_cannot_read_or_rate_another_student(self):
        self.assertEqual(self.batch(variant=0).status_code, 200)
        attempt = IndependentAttempt.objects.get(user=self.student, skill="transfer")
        self.client.force_login(self.other)
        res = self.client.post(self.url, {
            "action": "rubric", "attempt_id": attempt.pk,
            "rubric_meaning": "yes", "rubric_form": "yes",
            "rubric_context": "yes", "rubric_independence": "independent"})
        self.assertEqual(res.status_code, 404)
        self.assertNotContains(self.client.get(self.url), attempt.submitted)
