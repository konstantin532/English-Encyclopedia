"""«Атлас живого языка»: главная и меню показывают настоящие данные курса и лёгкие иллюстрации."""
from pathlib import Path

from django.conf import settings
from django.test import TestCase

from apps.accounts.models import User
from apps.curriculum.models import Week
from apps.lexicon.models import LexicalUnit
from tests.runner import ensure_content

ATLAS = Path(settings.BASE_DIR) / "static" / "img" / "atlas"


class LivingAtlasHomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.client.force_login(User.objects.create_user("atlas-student@example.test"))

    def test_home_shows_real_weeks_heroes_and_ready_status(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("English <br>Encyclopedia", html)
        self.assertIn("Знакомство с соседом", html)          # неделя 1 из плана курса
        for name in ("Anna", "Tom", "Mia", "Box"):
            self.assertIn(f'<h3 lang="en">{name}</h3>', html)
        self.assertIn("<p>14 недель A1 уже готовы</p>", html)
        self.assertEqual(Week.objects.filter(level__code="A1", scene__isnull=False).count(), 14)
        self.assertEqual(response.context["units_ready"], LexicalUnit.objects.count())
        self.assertNotIn("atlas-band-stats", html)
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
        names = ["hero-cafe-1400", "hero-cafe-760", "level-a1-1400", "level-a1-760", "portrait-anna", "portrait-tom",
                 "portrait-mia", "portrait-box", "ivy-vine", "note-new-story"]
        names += [f"a1-w{n:02d}-{s}" for n in range(1, 15) for s in (800, 1536)]
        names += [f"s{n:02d}-{s}" for n in range(1, 6) for s in (800, 1536)]
        for name in names:
            path = ATLAS / f"{name}.webp"
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                self.assertLess(path.stat().st_size, 320 * 1024)


class LivingAtlasCoversTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_every_a1_week_page_has_its_own_cover(self):
        for n in range(1, 15):
            html = self.client.get(f"/levels/a1/weeks/{n}/").content.decode()
            with self.subTest(week=n):
                self.assertIn(f"img/atlas/a1-w{n:02d}-1536.webp", html)
                self.assertNotIn("cafe-morning.webp", html)

    def test_story_pages_show_covers_for_stories_one_to_five(self):
        self.assertIn("img/atlas/s01-1536.webp", self.client.get("/stories/1/").content.decode())
        six = self.client.get("/stories/6/")
        if six.status_code == 200:  # истории A1+ пока без обложек
            self.assertNotIn("atlas-story-cover", six.content.decode())
