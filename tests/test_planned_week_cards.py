"""Неделя без темы показывает «Неделя N», а не «N ·» с пустым названием."""
from django.test import TestCase

from tests.runner import ensure_content


class PlannedWeekCardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_week_without_topic_has_no_dangling_dot(self):
        html = self.client.get("/levels/a1-plus/").content.decode()
        self.assertIn("<strong>Неделя 1</strong>", html)
        self.assertNotIn("<strong>1 · </strong>", html)

    def test_a1_weeks_keep_their_topic(self):
        html = self.client.get("/levels/a1/").content.decode()
        self.assertIn("<strong>1 · ", html)
        self.assertNotIn("<strong>Неделя 1</strong>", html)
