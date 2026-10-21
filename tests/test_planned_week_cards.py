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
        self.assertIn('<strong><span class="visually-hidden">Неделя 1: </span>Знакомство с соседом</strong>', html)
        self.assertNotIn("<strong>Неделя 1</strong>", html)

    def test_painted_covers_and_vector_fallback(self):
        html = self.client.get("/levels/a1/").content.decode()
        for n in (1, 4, 14):
            self.assertIn(f"img/atlas/a1-w{n:02d}-800.webp", html)  # обложки всех недель A1
        plus = self.client.get("/levels/a1-plus/").content.decode()
        self.assertIn('class="atlas-week-placeholder"', plus)
