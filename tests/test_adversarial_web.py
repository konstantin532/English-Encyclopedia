"""Повреждённые запросы не должны менять прогресс или ронять страницы."""
import json
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.drills.models import Exercise
from apps.learning.models import ExerciseAttempt, Status, UnitProgress
from apps.learning.services import RecallItem, build_review
from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit
from apps.curriculum.models import Level, Week
from apps.poems.models import Poem
from apps.stories.models import Story


class AnswerBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", stdout=StringIO())
        cls.user = User.objects.create_user("boundary@example.com", "boundary-password-123")
        cls.exercise = Exercise.objects.get(lesson__slug="a1-nouns-first-words", order=1)

    def setUp(self):
        self.client = Client(raise_request_exception=False)
        self.client.force_login(self.user)
        self.urls = [
            reverse("api:check_exercise", args=[self.exercise.pk]),
            reverse("api:recall_unit", args=["LX-00001"]),
            reverse("api:check_poem_gap", args=[1, 0]),
        ]

    def assert_rejected_without_progress(self, payload):
        for url in self.urls:
            with self.subTest(url=url, payload=repr(payload)):
                response = self.client.post(url, payload, content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertFalse(ExerciseAttempt.objects.exists())
                self.assertFalse(UnitProgress.objects.exists())

    def test_json_root_must_be_an_object(self):
        for value in [None, [], ["phone"], "phone", 1, True]:
            self.assert_rejected_without_progress(json.dumps(value))

    def test_non_text_answers_are_rejected_instead_of_stringified(self):
        for value in [None, [], {}, True, 17, "\ud800"]:
            self.assert_rejected_without_progress(json.dumps({"answer": value}))

    def test_missing_and_blank_answers_are_rejected_consistently(self):
        for value in [{}, {"answer": ""}, {"answer": " \n\t"}]:
            self.assert_rejected_without_progress(json.dumps(value))

    def test_reveal_must_be_a_boolean(self):
        for value in ["false", "true", 1, [], {}]:
            self.assert_rejected_without_progress(json.dumps({"reveal": value, "answer": "phone"}))

    def test_oversize_answers_are_not_saved_truncated(self):
        self.assert_rejected_without_progress(json.dumps({"answer": "x" * 201}))

    def test_invalid_json_encoding_is_a_client_error(self):
        for payload in [b"\xff", b'{"answer":', b'{"answer":"\xff"}']:
            self.assert_rejected_without_progress(payload)

    def test_reveal_does_not_record_a_correct_attempt(self):
        for url in self.urls:
            with self.subTest(url=url):
                response = self.client.post(url, json.dumps({"reveal": True}), content_type="application/json")
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.json()["correct"])
                self.assertIn("answer", response.json())
        self.assertFalse(ExerciseAttempt.objects.exists())
        self.assertFalse(UnitProgress.objects.exists())

    def test_invalid_request_preserves_existing_progress(self):
        unit = LexicalUnit.objects.get(uid="LX-00001")
        progress = UnitProgress.objects.create(user=self.user, unit=unit, correct_count=3, wrong_count=1,
                                               status=Status.INDEPENDENT_USE, stage=2)
        self.client.post(self.urls[1], json.dumps({"answer": None}), content_type="application/json")
        progress.refresh_from_db()
        self.assertEqual((progress.correct_count, progress.wrong_count, progress.stage), (3, 1, 2))


class AccountBoundaryTests(TestCase):
    def test_empty_signup_post_displays_required_field_errors(self):
        response = self.client.post(reverse("accounts:signup"), {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].is_bound)
        self.assertIn("email", response.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_marker_toggle_cannot_redirect_to_another_site(self):
        user = User.objects.create_user("redirect@example.com", "boundary-password-123")
        self.client.force_login(user)
        for target in ["https://evil.example/", "//evil.example/", "javascript:alert(1)", "https:///evil.example/"]:
            with self.subTest(target=target):
                response = self.client.post(reverse("learning:toggle_markers"), {"next": target})
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response["Location"], reverse("learning:dashboard"))

    def test_marker_toggle_preserves_a_local_destination(self):
        user = User.objects.create_user("local@example.com", "boundary-password-123")
        self.client.force_login(user)
        response = self.client.post(reverse("learning:toggle_markers"), {"next": "/words/?level=A1"})
        self.assertEqual(response["Location"], "/words/?level=A1")


class ReviewPublicationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", stdout=StringIO())
        cls.user = User.objects.create_user("review-boundary@example.com", "boundary-password-123")

    def test_review_does_not_assign_an_unpublished_lesson(self):
        exercise = Exercise.objects.get(lesson__slug="a1-nouns-first-words", order=1)
        unit = exercise.units.first()
        self.assertIsNotNone(unit)
        Lesson.objects.filter(units=unit).update(is_published=False)
        UnitProgress.objects.create(user=self.user, unit=unit, status=Status.RECOGNITION,
                                    next_review_at=timezone.now() - timedelta(days=1))
        items = build_review(self.user)
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0], RecallItem)

    def test_progress_and_review_do_not_leak_between_learners(self):
        other = User.objects.create_user("other-boundary@example.com", "boundary-password-123")
        unit = LexicalUnit.objects.get(uid="LX-00001")
        UnitProgress.objects.create(user=other, unit=unit, status=Status.RECOGNITION,
                                    next_review_at=timezone.now() - timedelta(days=1))
        self.assertEqual(build_review(self.user), [])


class PublicPageSweepTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", stdout=StringIO())

    def test_all_published_content_and_planned_weeks_are_accessible(self):
        urls = ["/", "/markers/", "/words/", "/stories/", "/accounts/login/", "/accounts/signup/"]
        urls += [reverse("curriculum:level", args=[level.slug]) for level in Level.objects.all()]
        urls += [reverse("curriculum:week", args=[week.level.slug, week.number])
                 for week in Week.objects.select_related("level")]
        urls += [reverse("lessons:detail", args=[lesson.slug]) for lesson in Lesson.objects.filter(is_published=True)]
        urls += [f"/words/{unit.uid}/" for unit in LexicalUnit.objects.all()]
        urls += [reverse("stories:detail", args=[story.number]) for story in Story.objects.filter(is_published=True)]
        urls += [f"/stories/poems/{poem.number}/" for poem in Poem.objects.filter(is_published=True)]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_search_handles_html_quotes_and_unknown_filters(self):
        response = self.client.get("/words/", {"q": '<script>alert("x")</script>'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<script>alert("x")</script>')
        for params in [{"q": "' OR 1=1 --"}, {"q": "я" * 1000}, {"level": "unknown", "cat": "Z999"}]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get("/words/", params).status_code, 200)
