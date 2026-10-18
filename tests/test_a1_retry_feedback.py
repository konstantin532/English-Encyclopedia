"""Original A1 lessons 1–4 keep their questions; hints diagnose without leaking keys."""
import json

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.drills.models import Exercise
from apps.drills.retry_guidance import PILOT_SLUGS, retry_guidance
from apps.learning.models import MistakeReview
from tests.runner import ensure_content


class A1FeedbackTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_all_original_questions_have_an_authored_focus(self):
        data = json.loads((settings.CONTENT_DIR / "manifests" / "a1_retry_guidance.json").read_text("utf-8"))
        self.assertEqual(set(data), PILOT_SLUGS)
        self.assertEqual(sum(len(items) for items in data.values()), 21)
        for slug, items in data.items():
            for ex in Exercise.objects.filter(lesson__slug=slug):
                with self.subTest(slug=slug, order=ex.order):
                    focus = items[str(ex.order)]["focus"]
                    self.assertGreater(len(focus), 20)
                    self.assertEqual(retry_guidance(ex, "unexpected"), focus)

    def test_wrong_choice_gives_specific_feedback_but_no_answer(self):
        ex = Exercise.objects.get(lesson__slug="a1-verb-be", order=2)
        response = self.client.post(reverse("api:check_exercise", args=[ex.pk]),
                                    json.dumps({"answer": "is"}), content_type="application/json")
        data = response.json()
        self.assertFalse(data["correct"])
        self.assertIn("feedback_ru", data)
        self.assertIn("he", data["feedback_ru"])
        self.assertNotIn("answer", data)
        self.assertNotIn("explanation", data)
        self.assertFalse(MistakeReview.objects.exists())  # guest does not schedule

    def test_open_response_not_mistaken_for_incorrect_grammar(self):
        ex = Exercise.objects.get(lesson__slug="a1-nouns-first-words", order=4)
        response = self.client.post(reverse("api:check_exercise", args=[ex.pk]),
                                    json.dumps({"answer": "I have a new book."}),
                                    content_type="application/json")
        data = response.json()
        self.assertEqual(data["assessment"], "needs_review")
        self.assertFalse(data["saved"])
        self.assertIn("feedback_ru", data)
        self.assertNotIn("answer", data)

    def test_correct_original_answer_retains_standard_explanation(self):
        ex = Exercise.objects.get(lesson__slug="a1-verb-be", order=2)
        response = self.client.post(reverse("api:check_exercise", args=[ex.pk]),
                                    json.dumps({"answer": "are"}), content_type="application/json")
        self.assertTrue(response.json()["correct"])
        self.assertIn("explanation", response.json())
