"""Rendered contracts for the progressively enhanced week page."""
import re
from html.parser import HTMLParser
from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from apps.curriculum.models import Week
from tests.runner import ensure_content

ROOT = Path(__file__).resolve().parent.parent


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class WeekMotionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def page(self, slug, number=None):
        route = "curriculum:level" if number is None else "curriculum:week"
        response = self.client.get(reverse(route, args=[slug] if number is None else [slug, number]))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_plugins_have_the_same_version_as_core(self):
        vendor = ROOT / "static/vendor/gsap"
        version = re.search(r"GSAP ([\d.]+)", (vendor / "gsap.min.js").read_text()).group(1)
        for name in ("Flip", "ScrollTrigger", "SplitText"):
            with self.subTest(plugin=name):
                path = vendor / f"{name}.min.js"
                self.assertTrue(path.is_file(), f"Missing {name}")
                self.assertIn(f"{name} {version}", path.read_text())

    def test_catalogue_names_are_unique_and_match_every_week_cover(self):
        catalogue = self.page("a1")
        names = re.findall(r"view-transition-name:\s*([\w-]+)", catalogue)
        self.assertTrue(names, "Catalogue needs shared title and cover identities")
        self.assertEqual(len(names), len(set(names)))
        for number in (1, 3, 13):
            with self.subTest(week=number):
                html = self.page("a1", number)
                tags = Tags(html).tags
                titles = [(tag, attrs) for tag, attrs in tags if "data-week-title" in attrs]
                self.assertEqual(len(titles), 1)
                self.assertEqual(titles[0][0], "h1")
                self.assertIn(f"week-a1-{number}-title", titles[0][1]["style"])
                for kind in ("title", "cover"):
                    self.assertEqual(names.count(f"week-a1-{number}-{kind}"), 1)
                    self.assertIn(f"view-transition-name: week-a1-{number}-{kind}", html)

    def test_lesson_disclosures_start_open_and_keep_real_links_and_summaries(self):
        html = self.page("a1", 1)
        cards = [attrs for tag, attrs in Tags(html).tags if tag == "details" and "data-week-flip" in attrs]
        week = Week.objects.get(level__code="A1", number=1)
        lessons = list(week.lessons.filter(is_published=True))
        self.assertEqual(len(cards), len(lessons))
        self.assertTrue(cards)
        self.assertTrue(all("open" in attrs for attrs in cards))
        for lesson in lessons:
            self.assertIn(reverse("lessons:detail", args=[lesson.slug]), html)
            self.assertIn(lesson.summary, html)

    def test_only_week_loads_plugins_after_core_in_deferred_order(self):
        week = self.page("a1", 1)
        scripts = [attrs for tag, attrs in Tags(week).tags if tag == "script" and attrs.get("src")]
        paths = [attrs["src"] for attrs in scripts]
        chain = ["gsap.min.js", "Flip.min.js", "ScrollTrigger.min.js", "SplitText.min.js", "week-motion.js"]
        for name in chain:
            self.assertTrue(any(path.endswith(name) for path in paths), f"Missing script {name}")
        indices = [next(i for i, path in enumerate(paths) if path.endswith(name)) for name in chain]
        self.assertEqual(indices, sorted(indices))
        self.assertTrue(all("defer" in scripts[index] for index in indices))
        level = self.page("a1")
        self.assertIn("css/week-motion.css", level)
        for name in chain[1:]:
            self.assertNotIn(name, level)
