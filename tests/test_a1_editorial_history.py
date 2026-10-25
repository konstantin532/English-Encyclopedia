"""Content reload preserves learner evidence; new pilot attempts use new tasks."""
import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, tag
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.drills.models import Exercise, PracticeItem
from apps.learning.models import ExerciseAttempt, IndependentAttempt, UnitProgress
from apps.learning.transfer_pilot import PILOTS
from apps.lessons.models import Lesson
from tests.runner import ensure_content

HAVE = "a1-have-like-can-do"
LEGACY_PROMPT = "Гость впервые у вас дома. Покажите одну вещь и вежливо предложите воду. Напишите 1–3 простые английские фразы."
LEGACY_MODEL = "This is my room. Would you like some water?"
CURRENT_PROMPT = "Гость впервые у вас дома. Покажите одну свою вещь и спросите, нравится ли она ему. Напишите 1–3 простые английские фразы."
CURRENT_MODEL = "This is my new table. Do you like it?"


class EditorialHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.user = User.objects.create_user(email="editorial-history@example.test", password="ExamplePassword123!")
        self.client.force_login(self.user)
        self.lesson = Lesson.objects.get(slug=HAVE)

    @tag("slow")
    def test_reload_keeps_existing_snapshots_attempts_and_content_identity(self):
        legacy = IndependentAttempt.objects.create(
            user=self.user, lesson=self.lesson, skill="transfer", task_variant=102,
            batch_token="pilot-existing-editorial-evidence", submitted="This is my room. Water?",
            prompt_snapshot=LEGACY_PROMPT, model_snapshot=LEGACY_MODEL,
            outcome=IndependentAttempt.Outcome.SELF_REPORTED,
            assistance=IndependentAttempt.Assistance.NOTES,
            self_rubric={"pilot_stage": "day_30", "planned_at": "2026-10-01T12:00:00+00:00",
                        "actual_submit_at": "2026-10-01T12:01:00+00:00", "timing": "within_one_day"},
        )
        exercise = Exercise.objects.get(uid="EX-00004")
        response = self.client.post(f"/api/exercises/{exercise.pk}/check/",
                                    json.dumps({"answer": exercise.answer}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["correct"])
        practice = PracticeItem.objects.get(lesson=self.lesson, order=1)
        response = self.client.post(f"/api/practice/{practice.pk}/check/",
                                    json.dumps({"answer": practice.answer}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["correct"])
        self.assertTrue(UnitProgress.objects.filter(user=self.user).exists())
        identity = {
            "lessons": list(Lesson.objects.filter(level__code="A1", order__lte=4)
                            .order_by("slug").values_list("pk", "slug", "order")),
            "exercises": list(Exercise.objects.filter(lesson__level__code="A1", lesson__order__lte=4)
                              .order_by("uid").values_list("pk", "uid", "lesson_id", "order")),
            "practice": list(PracticeItem.objects.filter(lesson__level__code="A1", lesson__order__lte=4)
                             .order_by("lesson_id", "order").values_list("pk", "lesson_id", "order", "review_of")),
        }
        snapshots = list(IndependentAttempt.objects.filter(pk=legacy.pk).values())
        attempts = list(ExerciseAttempt.objects.filter(user=self.user).order_by("pk").values())
        progress = list(UnitProgress.objects.filter(user=self.user).order_by("pk").values())
        call_command("load_content", stdout=StringIO())
        self.assertEqual(list(IndependentAttempt.objects.filter(pk=legacy.pk).values()), snapshots)
        self.assertEqual(list(ExerciseAttempt.objects.filter(user=self.user).order_by("pk").values()), attempts)
        self.assertEqual(list(UnitProgress.objects.filter(user=self.user).order_by("pk").values()), progress)
        self.assertEqual(list(Lesson.objects.filter(level__code="A1", order__lte=4)
                              .order_by("slug").values_list("pk", "slug", "order")), identity["lessons"])
        self.assertEqual(list(Exercise.objects.filter(lesson__level__code="A1", lesson__order__lte=4)
                              .order_by("uid").values_list("pk", "uid", "lesson_id", "order")), identity["exercises"])
        self.assertEqual(list(PracticeItem.objects.filter(lesson__level__code="A1", lesson__order__lte=4)
                              .order_by("lesson_id", "order").values_list("pk", "lesson_id", "order", "review_of")), identity["practice"])
        exercise.refresh_from_db()
        self.assertEqual(ExerciseAttempt.objects.get(user=self.user, exercise=exercise).exercise.uid, "EX-00004")

    def test_day_thirty_uses_revised_task_and_preserves_schedule_and_skill(self):
        now = timezone.now().replace(microsecond=0)
        first_time = now - timedelta(days=30)
        first = IndependentAttempt.objects.create(
            user=self.user, lesson=self.lesson, skill="transfer", task_variant=100,
            batch_token="pilot-initial-editorial", created_at=first_time,
            submitted="I have a book. I like it.", prompt_snapshot="Original initial prompt",
            model_snapshot="Original initial model", outcome=IndependentAttempt.Outcome.SELF_REPORTED,
        )
        url = reverse("learning:transfer_pilot", args=[HAVE])
        with patch("apps.learning.transfer_pilot.timezone.now", return_value=now - timedelta(seconds=1)):
            early = self.client.get(url)
            self.assertEqual(early.context["stage"], ("day_30", 102, 30))
            self.assertFalse(early.context["ready"])
            self.assertEqual(early.context["due_at"], first_time + timedelta(days=30))
        with patch("apps.learning.transfer_pilot.timezone.now", return_value=now):
            page = self.client.get(url)
            self.assertTrue(page.context["ready"])
            self.assertEqual(page.context["stage"], ("day_30", 102, 30))
            self.assertEqual(page.context["mission"], {"prompt": CURRENT_PROMPT, "model": CURRENT_MODEL})
            self.assertEqual(page.context["mission"], PILOTS[HAVE]["missions"][2])
            form = {"token": page.context["token"], "stage": "102", "answer": CURRENT_MODEL,
                    "assistance": "no_help"}
            self.assertEqual(self.client.post(url, form).status_code, 302)
            self.assertEqual(self.client.post(url, form).status_code, 400)
        saved = IndependentAttempt.objects.get(user=self.user, task_variant=102)
        self.assertEqual(saved.lesson_id, self.lesson.pk)
        self.assertEqual(saved.skill, "transfer")
        self.assertEqual(saved.prompt_snapshot, CURRENT_PROMPT)
        self.assertEqual(saved.model_snapshot, CURRENT_MODEL)
        self.assertEqual(saved.submitted, CURRENT_MODEL)
        self.assertEqual(saved.assistance, IndependentAttempt.Assistance.NO_HELP)
        self.assertEqual(saved.outcome, IndependentAttempt.Outcome.SELF_REPORTED)
        self.assertEqual(saved.teacher_verdict, IndependentAttempt.TeacherVerdict.UNREVIEWED)
        self.assertEqual(saved.self_rubric["pilot_stage"], "day_30")
        self.assertEqual(saved.self_rubric["planned_at"], now.isoformat())
        self.assertEqual(saved.self_rubric["actual_submit_at"], now.isoformat())
        self.assertEqual(saved.self_rubric["timing"], "within_one_day")
        self.assertFalse(IndependentAttempt.objects.filter(user=self.user, task_variant=101).exists())
        self.assertFalse(UnitProgress.objects.filter(user=self.user).exists())
        self.assertFalse(ExerciseAttempt.objects.filter(user=self.user).exists())
        first.refresh_from_db()
        self.assertEqual(first.prompt_snapshot, "Original initial prompt")
        self.assertEqual(first.model_snapshot, "Original initial model")
