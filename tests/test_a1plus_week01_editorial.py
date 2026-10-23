"""Targeted A1+ week-one meaning and accepted-answer regressions.

These checks do not replace a human ELT review or learner comprehension tests.
"""
import json
from pathlib import Path

import yaml
from django.test import SimpleTestCase, TestCase

from apps.drills.models import PracticeItem
from tests.runner import ensure_content


LESSONS = Path(__file__).resolve().parents[1] / "content" / "seed_lessons"


class A1PlusWeek01ExplanationsTests(SimpleTestCase):
    def test_video_call_contrasts_hearing_with_listening(self):
        lesson = yaml.safe_load(
            (LESSONS / "a1p_w01_l02_video_call.yaml").read_text(encoding="utf-8")
        )
        second_layer = next(
            layer["body"] for layer in lesson["layers"] if layer["number"] == 2
        )
        self.assertIn("Can you hear me?", second_layer)
        self.assertIn("Are you listening to me?", second_layer)
        self.assertIn("listen to me", second_layer)
        self.assertIn("I can hear you", second_layer)
        self.assertIn("I'm listening to you", second_layer)
        self.assertIn("I miss you", second_layer)

    def test_present_continuous_accepts_explicit_now_qualifiers(self):
        lesson = yaml.safe_load(
            (LESSONS / "a1p_w01_l01_present_continuous.yaml").read_text(
                encoding="utf-8"
            )
        )
        practice = {item["order"]: item for item in lesson["practice"]}
        self.assertIn("She is writing a letter right now.", practice[2]["accepted"])
        self.assertIn("She's writing a letter now.", practice[2]["accepted"])
        self.assertIn("We are cleaning the kitchen now.", practice[4]["accepted"])
        self.assertIn("We're cleaning the kitchen right now.", practice[4]["accepted"])


class A1PlusWeek01PracticeAnswerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def check_answer(self, order, answer, correct):
        item = PracticeItem.objects.get(
            lesson__slug="a1p-present-continuous", order=order
        )
        response = self.client.post(
            f"/api/practice/{item.pk}/check/",
            json.dumps({"answer": answer}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["correct"], correct)

    def test_natural_variants_are_accepted(self):
        for order, answers in (
            (2, ("She is writing a letter right now.",
                 "She's writing a letter now.")),
            (4, ("We are cleaning the kitchen now.",
                 "We're cleaning the kitchen right now.")),
        ):
            for answer in answers:
                with self.subTest(order=order, answer=answer):
                    self.check_answer(order, answer, True)

    def test_missing_be_or_wrong_verb_form_are_rejected(self):
        for order, answer in (
            (2, "She writing a letter right now."),
            (4, "We cleaning the kitchen now."),
        ):
            with self.subTest(order=order, answer=answer):
                self.check_answer(order, answer, False)
