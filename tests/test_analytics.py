"""Аналитика урока и эксперименты: выключены без ключа и не отправляют личных данных."""

import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.core import analytics, experiments
from apps.drills.models import Exercise
from tests.runner import ensure_content

LESSON = "a1-verb-be"
EMAIL = "analytics-learner@example.test"


class DisabledByDefaultTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_no_key_means_no_client_and_no_events(self):
        self.assertEqual(analytics.enabled(), False)
        with patch.object(analytics, "get_client") as client:
            self.assertEqual(self.client.get(reverse("lessons:detail", args=[LESSON])).status_code, 200)
            exercise = Exercise.objects.filter(lesson__slug=LESSON).first()
            self.client.post(
                reverse("api:check_exercise", args=[exercise.pk]),
                json.dumps({"answer": "wrong-answer"}),
                content_type="application/json",
            )
        client.assert_not_called()

    def test_experiment_returns_default_without_key(self):
        request = RequestFactory().get("/")
        self.assertEqual(experiments.variant(request, "lesson-hint-style"), "rule-first")


class EventValidationTests(SimpleTestCase):
    def test_unknown_event_and_property_are_rejected_even_without_key(self):
        request = RequestFactory().get("/")
        with self.assertRaises(ValueError):
            analytics.capture(request, "page_view")
        with self.assertRaises(ValueError):
            analytics.capture(request, "lesson_opened", email=EMAIL)


@override_settings(POSTHOG_KEY="phc_test_only")
class EnabledEventsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.user = User.objects.create_user(email=EMAIL, password="local-only")
        cls.exercises = list(Exercise.objects.filter(lesson__slug=LESSON).order_by("order"))

    def setUp(self):
        self.posthog = MagicMock()
        patcher = patch.object(analytics, "get_client", return_value=self.posthog)
        patcher.start()
        self.addCleanup(patcher.stop)

    def events(self):
        return [(call.args[0], call.kwargs) for call in self.posthog.capture.call_args_list]

    def answer(self, exercise, answer):
        return self.client.post(
            reverse("api:check_exercise", args=[exercise.pk]),
            json.dumps({"answer": answer}),
            content_type="application/json",
        )

    def assert_no_personal_data(self, kwargs):
        properties = kwargs["properties"]
        self.assertLessEqual(set(properties) - {"$process_person_profile"}, analytics.PROPERTIES)
        self.assertIs(properties["$process_person_profile"], False)
        dumped = json.dumps(kwargs, default=str)
        self.assertNotIn(EMAIL, dumped)
        self.assertNotIn("wrong-answer", dumped)
        self.assertNotEqual(kwargs["distinct_id"], str(self.user.pk))

    def test_lesson_opened_uses_pseudonymous_id(self):
        self.client.force_login(self.user)
        self.client.get(reverse("lessons:detail", args=[LESSON]))
        [(event, kwargs)] = self.events()
        self.assertEqual(event, "lesson_opened")
        self.assertEqual(kwargs["properties"]["lesson"], LESSON)
        self.assertEqual(kwargs["properties"]["level"], "A1")
        self.assertIs(kwargs["properties"]["guest"], False)
        self.assertRegex(kwargs["distinct_id"], r"^[0-9a-f]{32}$")
        self.assert_no_personal_data(kwargs)

    def test_mistake_is_sent_without_the_answer_text(self):
        self.client.force_login(self.user)
        self.answer(self.exercises[0], "wrong-answer")
        [(event, kwargs)] = self.events()
        self.assertEqual(event, "exercise_mistake")
        self.assertEqual(kwargs["properties"]["exercise"], self.exercises[0].order)
        self.assert_no_personal_data(kwargs)

    def test_lesson_completed_once_after_every_exercise_is_solved(self):
        self.client.force_login(self.user)
        for exercise in self.exercises:
            self.answer(exercise, exercise.answer)
        names = [event for event, _ in self.events()]
        self.assertEqual(names, ["lesson_completed"])
        self.answer(self.exercises[-1], self.exercises[-1].answer)
        self.assertEqual([event for event, _ in self.events()], ["lesson_completed"])

    def test_posthog_failure_does_not_break_the_lesson(self):
        self.posthog.capture.side_effect = RuntimeError("PostHog is down")
        with self.assertLogs("apps.analytics", level="WARNING"):
            response = self.client.get(reverse("lessons:detail", args=[LESSON]))
        self.assertEqual(response.status_code, 200)

    def test_experiment_accepts_only_known_variants(self):
        request = RequestFactory().get("/")
        request.user = self.user
        self.posthog.get_feature_flag.return_value = "example-first"
        self.assertEqual(experiments.variant(request, "lesson-hint-style"), "example-first")
        self.posthog.get_feature_flag.return_value = "something-else"
        self.assertEqual(experiments.variant(request, "lesson-hint-style"), "rule-first")
        self.posthog.get_feature_flag.side_effect = TimeoutError
        with self.assertLogs("apps.experiments", level="WARNING"):
            self.assertEqual(experiments.variant(request, "lesson-hint-style"), "rule-first")
