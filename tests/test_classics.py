"""«Классика»: легендарные скороговорки и стихи, свободные от авторских прав."""
from django.test import TestCase

from apps.core.classics import PUBLIC_DOMAIN_BEFORE, classics


class ClassicsContentTests(TestCase):
    def test_eight_twisters_and_five_poems(self):
        data = classics()
        self.assertEqual(len(data["twisters"]), 8)
        self.assertEqual(len(data["poems"]), 5)

    def test_poems_are_public_domain(self):
        for poem in classics()["poems"]:
            self.assertLess(poem["year"], PUBLIC_DOMAIN_BEFORE, poem["slug"])

    def test_every_line_and_card_is_explained(self):
        data = classics()
        for t in data["twisters"]:
            for key in ("text", "ru", "sounds", "ipa", "tip_ru", "why_ru"):
                self.assertTrue(t.get(key), (t["slug"], key))
            self.assertTrue(all(t["glossary"].values()), t["slug"])
        for p in data["poems"]:
            self.assertTrue(p["lines"] and all(len(line) == 2 and all(line) for line in p["lines"]), p["slug"])
            self.assertTrue(p["about_ru"] and p["learn_ru"] and all(p["glossary"].values()), p["slug"])

    def test_slugs_are_unique(self):
        data = classics()
        slugs = [x["slug"] for x in data["twisters"] + data["poems"]]
        self.assertEqual(len(slugs), len(set(slugs)))


class ClassicsPageTests(TestCase):
    def test_page_renders_with_listen_buttons_and_translations(self):
        html = self.client.get("/classics/").content.decode()
        self.assertIn("Легендарные скороговорки", html)
        self.assertIn("She sells seashells by the seashore.", html)
        self.assertIn("Hold fast to dreams", html)
        self.assertIn("Держись за мечты,", html)
        self.assertIn("Langston Hughes", html)
        self.assertGreaterEqual(html.count("data-speak-rate"), 26)
        self.assertIn("classics-speech.js", html)

    def test_sidebar_links_to_classics(self):
        html = self.client.get("/").content.decode()
        self.assertIn('href="/classics/"', html)
