"""Regression: speech review must be real, private and separate from vocabulary score."""
import json
from datetime import datetime, timedelta, timezone as tz

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.learning.models import SpeechPracticeProgress
from apps.learning.speech_practice import content_details
from apps.lessons.models import Lesson
from tests.runner import ensure_content


class OralReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.user = get_user_model().objects.create_user(
            email="speech-learner@example.com", password="test-password"
        )
        cls.lesson = Lesson.objects.get(level__code="A1", order=1)
        cls.key = "lesson:" + cls.lesson.slug

    def setUp(self):
        self.client.force_login(self.user)

    def send(self, key=None, index=0, rating="good"):
        return self.client.post(
            reverse("learning:speech_practice"),
            data=json.dumps({"key": key or self.key, "index": index, "rating": rating}),
            content_type="application/json",
        )

    def test_real_course_content_only_and_fragment_counts(self):
        self.assertEqual(content_details(self.key)["count"], 6)
        self.assertGreaterEqual(content_details("twister:1")["count"], 2)
        self.assertEqual(content_details("poem:1")["count"], 16)
        for key in ("lesson:fake-lesson", "twister:999", "poem:999", "lesson:../../secret",
                    "lesson:a!b", "poem:0", "poem:01", "a" * 200):
            self.assertIsNone(content_details(key), key)

    def test_difficulty_rating_changes_due_schedule_and_is_user_scoped(self):
        now = datetime(2026, 10, 18, 9, tzinfo=tz.utc)
        p = SpeechPracticeProgress(user=self.user, content_key=self.key, fragment=0)
        p.register("good", now=now)
        self.assertEqual(p.stage, 1)
        self.assertEqual(p.next_review_at, now + timedelta(days=1))
        p.register("good", now=now)
        self.assertEqual(p.stage, 2)
        self.assertEqual(p.next_review_at, now + timedelta(days=3))
        p.register("hard", now=now)
        self.assertEqual(p.stage, 1)
        self.assertEqual(p.next_review_at, now + timedelta(days=1))
        p.register("again", now=now)
        self.assertEqual(p.stage, 0)
        self.assertEqual(p.next_review_at, now)
        self.assertEqual(p.attempts, 4)
        with self.assertRaises(ValueError):
            p.register("perfect", now=now)

    def test_post_and_get_roundtrip_and_due_page(self):
        response = self.send()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["due"])
        self.assertEqual(SpeechPracticeProgress.objects.filter(user=self.user).count(), 1)
        self.assertEqual(response.json()["stage"], 1)
        self.assertNotIn("audio", response.json())
        progress = self.client.get(reverse("learning:speech_practice"), {"key": self.key})
        self.assertEqual(progress.status_code, 200)
        self.assertEqual(progress.json()["count"], 6)
        self.assertEqual(len(progress.json()["items"]), 1)
        self.assertEqual(self.send(rating="again").status_code, 200)
        due = self.client.get(reverse("learning:speech_review"))
        self.assertEqual(due.status_code, 200)
        self.assertContains(due, "?speech=0#spoken-coach")
        self.assertContains(due, self.lesson.title)
        dashboard = self.client.get(reverse("learning:dashboard"))
        self.assertContains(dashboard, "Речевые повторения (1)")

    def test_validation_does_not_create_phantom_progress(self):
        for key, index, rating in [
            ("lesson:not-real", 0, "good"), (self.key, -1, "good"),
            (self.key, 6, "good"), (self.key, True, "good"),
            (self.key, "0", "good"), (self.key, 0, "perfect"),
            ("twister:1", 999, "again"), ("poem:1", 16, "hard"),
        ]:
            with self.subTest(key=key, index=index, rating=rating):
                self.assertEqual(self.send(key, index, rating).status_code, 400)
        self.assertFalse(SpeechPracticeProgress.objects.filter(user=self.user).exists())
        self.assertEqual(self.client.post(
            reverse("learning:speech_practice"), data="{bad", content_type="application/json"
        ).status_code, 400)

    def test_malformed_or_oversized_audio_review_requests_do_not_create_progress(self):
        url = reverse("learning:speech_practice")
        packets = (
            b'{"key":"lesson:a","padding":"' + b'x' * 16_384 + b'"}',
            b'[' * 1100 + b'0' + b']' * 1100,
            bytes([0xff]),
        )
        for payload in packets:
            with self.subTest(length=len(payload)):
                result = self.client.post(url, data=payload, content_type="application/json")
                self.assertEqual(result.status_code, 400)
        self.assertFalse(SpeechPracticeProgress.objects.filter(user=self.user).exists())

    def test_stale_history_cannot_starve_a_valid_due_review(self):
        old = timezone.now() - timedelta(days=5)
        SpeechPracticeProgress.objects.bulk_create([
            SpeechPracticeProgress(
                user=self.user, content_key=f"lesson:removed-{i}",
                fragment=0, next_review_at=old,
            )
            for i in range(120)
        ])
        SpeechPracticeProgress.objects.create(
            user=self.user, content_key=self.key, fragment=0,
            next_review_at=old + timedelta(days=1),
        )
        response = self.client.get(reverse("learning:speech_review"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "?speech=0#spoken-coach")
        self.assertContains(response, self.lesson.title)

    def test_anonymous_and_csrf_requirements(self):
        self.client.logout()
        self.assertEqual(self.send().status_code, 302)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        response = strict.post(
            reverse("learning:speech_practice"),
            data=json.dumps({"key": self.key, "index": 0, "rating": "good"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_user_b_cannot_read_a_progress(self):
        self.assertEqual(self.send().status_code, 200)
        second = get_user_model().objects.create_user(
            email="other-speech@example.com", password="another-test-password"
        )
        self.client.force_login(second)
        response = self.client.get(reverse("learning:speech_practice"), {"key": self.key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertNotContains(self.client.get(reverse("learning:speech_review")), self.lesson.title)

    def test_studios_expose_stable_keys_and_review_client(self):
        for n in (1, 13, 26):
            lesson = Lesson.objects.get(level__code="A1", order=n)
            response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
            self.assertContains(response, "data-speech-key=\"lesson:" + lesson.slug + "\"")
            self.assertContains(response, "speech-review.js")
        response = self.client.get(reverse("curriculum:week", args=["a1", 1]))
        self.assertContains(response, 'data-speech-key="twister:1"')
        self.assertContains(response, "speech-review.js")
        response = self.client.get(reverse("stories:poem", args=[1]))
        self.assertContains(response, 'data-speech-key="poem:1"')
        self.assertContains(response, "speech-review.js")
