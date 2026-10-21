"""«Атлас живого языка»: главная и меню показывают настоящие данные курса и лёгкие иллюстрации."""
from pathlib import Path

from django.conf import settings
from django.test import TestCase

from apps.lexicon.models import LexicalUnit
from tests.runner import ensure_content

ATLAS = Path(settings.BASE_DIR) / "static" / "img" / "atlas"


class LivingAtlasHomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_home_shows_real_weeks_heroes_and_counts(self):
        html = self.client.get("/").content.decode()
        self.assertIn("English <br>Encyclopedia", html)
        self.assertIn("Знакомство с соседом", html)          # неделя 1 из плана курса
        for name in ("Anna", "Tom", "Mia", "Box"):
            self.assertIn(f'<h3 lang="en">{name}</h3>', html)
        self.assertIn(f"<dd>{LexicalUnit.objects.count()}</dd>", html)  # цифры из базы, а не с макета
        self.assertNotIn("рейтинг", html.lower())

    def test_phrase_widget_markup_survives(self):
        html = self.client.get("/").content.decode()
        self.assertIn("data-language-atlas", html)
        self.assertIn("Я дома. Два слова — целая мысль.", html)
        self.assertEqual(html.count("data-atlas-role="), 3)

    def test_sidebar_is_shared_and_marks_current_page(self):
        html = self.client.get("/levels/a1/").content.decode()
        self.assertIn('class="studio-sidebar atlas-sidebar"', html)
        self.assertIn("living-atlas.css", html)
        self.assertRegex(html, r'href="/levels/a1/" aria-current="page"><svg')

    def test_illustrations_exist_and_stay_light(self):
        names = ["hero-anna-1600", "hero-anna-800", "level-a1-1600", "portrait-anna", "portrait-tom",
                 "portrait-mia", "portrait-box", "ivy-vine", "note-new-story"]
        names += [f"a1-w{n:02d}-{s}" for n in (1, 2, 3, 10, 11) for s in (800, 1600)]
        for name in names:
            path = ATLAS / f"{name}.webp"
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertLess(path.stat().st_size, 320 * 1024)
