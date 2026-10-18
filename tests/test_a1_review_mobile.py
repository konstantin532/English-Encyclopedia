"""Mobile and keyboard acceptance contracts for the delayed A1 review page.

This verifies rendered semantics and CSS invariants; a real Android browser
check is still a separate manual/device QA activity.
"""
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.drills.models import Exercise
from apps.learning.models import MistakeReview
from tests.runner import ensure_content


class MobileMistakeReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.user = User.objects.create_user(
            email="mobile-review@example.test", password="MobileQaPass123!"
        )
        self.client.force_login(self.user)

    def test_during_due_review_html_has_accessible_touch_selection(self):
        source = Exercise.objects.get(lesson__slug="a1-review-everything", order=1)
        item = MistakeReview.objects.create(
            user=self.user, exercise=source, due_at=timezone.now()
        )
        page = self.client.get(reverse("learning:mistake_review"))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'name="viewport" content="width=device-width, initial-scale=1"')
        self.assertContains(page, 'css/mistake-review.css')
        self.assertContains(page, 'class="mistake-review-options"')
        self.assertContains(page, 'class="mistake-review-option"', count=3)
        self.assertContains(page, 'name="choice"', count=3)
        self.assertContains(page, 'type="radio"', count=3)
        self.assertContains(page, 'type="submit"')
        self.assertContains(page, "Выберите ответ")
        self.assertContains(page, "Новый вопрос 1 из 5")
        # Correct answer is not exposed in hidden inputs or form attributes.
        self.assertNotContains(page, 'name="correct"')
        self.assertNotContains(page, 'name="answer"')
        self.assertNotContains(page, "data-answer=")

    def test_mobile_css_touch_targets_and_overflow_safeguards(self):
        source = (
            Path(settings.BASE_DIR) / "static" / "css" / "mistake-review.css"
        ).read_text(encoding="utf-8")
        for rule in (
            "min-height: 52px", "min-height: 48px",
            "min-width: 0", "overflow-wrap: anywhere",
            ":focus-within", "@media (max-width: 480px)",
            "prefers-reduced-motion: reduce",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, source)

    def test_without_pending_review_has_no_unnecessary_radio_controls(self):
        page = self.client.get(reverse("learning:mistake_review"))
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'type="radio"')
        self.assertContains(page, "Новых вопросов пока нет")
