"""Проверки раздела «Классика» и сроков охраны произведений."""
import base64
from copy import deepcopy
from hashlib import sha256
import re

from django.test import TestCase

from apps.core.classics import (
    PUBLIC_DOMAIN_BEFORE,
    RUSSIAN_COPYRIGHT_YEARS,
    classics,
    validate_classics_data,
)


# SHA-256 нормализованных последовательностей из пяти слов удалённых стихов.
# Храним только хеши, чтобы не восстанавливать в репозитории защищённые тексты.
# Нормализация: lowercase, слова [a-z]+, пробел между словами.
_PROTECTED_FIVEGRAM_HASHES = """
ARuz492LSRjXHiaVnuOhx1DAwE371t2Y6IFEo8N+hyQCrscMf/hOsDS4ODkiKFi1/pZdjCV0TxOXshuY04KclwLzo8AJzt4d9wZUiwFHKrBJv5iYeCEUXAHyFizZoUAxBaXs26OP16+K8JMkvAykcdjFu5SiclJ83usniWJiI/MH5B+LHkUztc49Q8GygsKLL8ol7kMr6yyVRFnEyRzaGQlqTCGlxnqzs2PZzSFUEfDGSObn2nsXrqUa89cJVJ+DDlIEzvqdbjMdt9DYLQpBfOIfmURzhrFp/+eKdmCSoAYOXvVJgWwQiDiy7MMmiHnBuOp5gm6RB5CScrplbmverBJALdzqeTf1+k4skE6u6xSBSx7o00XNhNu2KyD7mNktF6aJwa70iNrjO2Sr5tWZLLv+vERNXf47vykdX1XrdEMYxbLWCSLrCJX6Qzup/ykdjPsDKJM1kd0BxLx3M+y4bxvGqkuuS52kMfscMXQI8U1F3LOp7TTr//GquZtWHi82OEXW+kAEDk53khl5tguVwNu9fMjhPz7IW+9IUwAiuRs4m+ZTTQhXml5mXRjb5EPwsvrCQjKJCxq7J+C23u0o0TvLsX1UEJmQlM+AjfRjegZDuiLxqZa9O64ax5uWkhgOQVjN/LAwWqaye7JJIzeHqvX1SoQazMi9oerugkOXh5BK8Sc4kzq3QhPcIm0XJ/ukEAtAonlIoroCXq5POz6y0lIWd56vaaIFiwPYdVCdM+icTVfQZJyzKg8Kg8eDbE4QV5m7UKCjL6h9jrjDlMPFLeOUGpUI5ZjeWN3ogtnaDn1lZiT+5uPeUWnwwPWV2z+LpWb4PjFVhht4MbyTtkxsWWlbx19rKkTU8i1zNma9m7p8I0u68ZszmmezLvIueMDBdFZwE+v2aNSsgLbfmsF/vAxyMocuytJS1YDuTaRNAxx7KMReZelfLUTbjJnxMtApSVPpyTIBCIPk9RiYWh5d8Xvv5gShOAODPwC82gHd6glB/1/lIgUQAOEM1t8jNeDBglZ15L4AjFhjZlgZThdbrmY4Ep5HeEJu43AzMQnk2DWCcS569IyvwGdqXLgTpiH2lfC7Q8PT8IQn0Tivcw4vaJEtbzww0CfPFjKymA7jF5QQ7oq9Q3cDcMUpr43kvxzgmY+dMZK4Ru1NnPw1MydCBRFBr3IYlhD80YsiCzBlAgmZ009eaw7fVSEkHEdwtb6UAeHM0TFe4ymQMk8zmeRSiZrm6vZMGMcSX1Zg8Y+03pKz2AqM4nyE0rt/AxVh+GHKnJLoreOEIFC8Jxpc1F/WEx8a/hLgNE0hC6BCU6qSRAClSDcjWLW37pUqfxG9mPd8OmN+x1QMozmi+1AjmsjyB6eATkbPaN1i1xP8WIOwymQRzqBngp2wEp6ywy/GJVB9qN7qdKS9YpjJVylcyceV7UvHob5I286eYd3BO5AOM2OpZ0ShEqqqAHSSlwLR8ZGL6vVpqkYs151ZN29qNsqEmamZLOedd+ComXRzW8XMdDsqieRFg/78z56JI7l0nf+kwTpmnc0rw6lAJqQJL3QLP6xwu3gGEjB2UCnoqVsTQsrIgrbaZZSMr/VhvJuf5sdzlcwUzonz0TOtad9yk37y+co7qkGrYpyw6pErb9VzkftXksTzgm+Jk09slpLkv731yumLXOfCn4ZIXpWKqwwIn79rNEd7hHac+3pV7Fj+HunN1bKk1U7uO66F7o+I55kkUhmNUC8Dv3RkLFVcwoUGzdASshtcPBHAU0w393H/0eCrlde73oe/Q8sJcqRD3oic0JoT2grz0kxfG2zBpW0uN/OIqdj7WixfMDAH4niW6K3a4I5tXqHurfKvL5k1s2VSq+GqugiGSJfdkSa1cYZTy+eQlMzPPpMceWa9hLODQeGb75EZnK28fLZrVN1zm+yB
"""


def historical_poem(**overrides):
    poem = {
        "slug": "historical-poem",
        "author": "Example Author",
        "author_death_year": 1955,
        "year": 1900,
        "source_edition": "First edition, 1900",
        "source_url": "https://example.org/old-edition",
    }
    poem.update(overrides)
    return poem


class ClassicsContentTests(TestCase):
    def test_eight_twisters_and_seven_poems(self):
        data = classics()
        self.assertEqual(len(data["twisters"]), 8)
        self.assertEqual(len(data["poems"]), 7)
        self.assertEqual(
            {p["slug"] for p in data["poems"]},
            {
                "who-has-seen-the-wind", "im-nobody", "annas-map",
                "annas-misty-morning", "hickory-dickory-dock",
                "buckle-my-shoe", "mondays-child",
            },
        )

    def test_historical_poems_have_both_copyright_checks_and_sources(self):
        for poem in classics()["poems"]:
            if poem["author"] in ("folk", "original"):
                self.assertNotIn("author_death_year", poem)
            else:
                self.assertLess(poem["year"], PUBLIC_DOMAIN_BEFORE, poem["slug"])
                self.assertLess(
                    poem["author_death_year"] + RUSSIAN_COPYRIGHT_YEARS,
                    2026,
                    poem["slug"],
                )
                self.assertTrue(poem["source_edition"] and poem["source_url"])
        validate_classics_data(classics(), current_year=2026)

    def test_missing_author_or_death_year_rejected(self):
        for changes in ({"author": ""}, {"author_death_year": None}, {"author_death_year": "1950"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_classics_data({"poems": [historical_poem(**changes)]}, current_year=2026)

    def test_russian_life_plus_70_is_strict(self):
        for year in (1956, 1967):
            with self.subTest(year=year), self.assertRaises(ValueError):
                validate_classics_data(
                    {"poems": [historical_poem(author_death_year=year)]},
                    current_year=2026,
                )
        validate_classics_data({"poems": [historical_poem(author_death_year=1955)]}, current_year=2026)
        validate_classics_data({"poems": [historical_poem(author_death_year=1956)]}, current_year=2027)

    def test_historical_publication_after_us_cutoff_rejected(self):
        with self.assertRaises(ValueError):
            validate_classics_data(
                {"poems": [historical_poem(year=PUBLIC_DOMAIN_BEFORE)]},
                current_year=2026,
            )

    def test_historical_poem_must_cite_edition(self):
        with self.assertRaises(ValueError):
            validate_classics_data(
                {"poems": [historical_poem(source_url="")]}, current_year=2026
            )

    def test_folk_and_original_have_no_death_year(self):
        for author in ("folk", "original"):
            validate_classics_data({"poems": [{"slug": "test", "author": author, "year": 2026}]}, current_year=2026)
            with self.assertRaises(ValueError):
                validate_classics_data(
                    {"poems": [{"slug": "test", "author": author, "author_death_year": 1890}]},
                    current_year=2026,
                )

    def test_twisters_are_folk_or_expired_historical_authors(self):
        self.assertTrue(all(t["author"] == "folk" for t in classics()["twisters"]))
        for twister in (
            {"slug": "example", "author": "Composer", "author_death_year": 1956},
            {"slug": "example", "author": "Composer"},
            {"slug": "example"},
            {"slug": "example", "author": "original"},
        ):
            with self.subTest(twister=twister), self.assertRaises(ValueError):
                validate_classics_data({"twisters": [twister]}, current_year=2026)

    def test_original_poems_do_not_copy_five_consecutive_words(self):
        payload = base64.b64decode("".join(_PROTECTED_FIVEGRAM_HASHES.split()))
        self.assertEqual(len(payload), 45 * sha256().digest_size)
        forbidden = {payload[i:i + 32] for i in range(0, len(payload), 32)}
        self.assertEqual(len(forbidden), 45)
        original_count = 0
        for poem in classics()["poems"]:
            if poem["author"] != "original":
                continue
            original_count += 1
            words = re.findall(r"[a-z]+", " ".join(line[0] for line in poem["lines"]).lower())
            self.assertGreaterEqual(len(words), 5, poem["slug"])
            for i in range(len(words) - 4):
                digest = sha256(" ".join(words[i:i + 5]).encode("utf-8")).digest()
                self.assertNotIn(digest, forbidden, (poem["slug"], i))
        self.assertEqual(original_count, 2)

    def test_every_line_and_card_is_explained(self):
        data = classics()
        for t in data["twisters"]:
            for key in ("text", "ru", "sounds", "ipa", "tip_ru", "why_ru", "author"):
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
        self.assertIn("Christina Rossetti", html)
        self.assertIn("Emily Dickinson", html)
        self.assertIn("A Circle on the Map", html)
        self.assertIn("The Morning Without Edges", html)
        self.assertIn("Издание:", html)
        self.assertGreaterEqual(html.count("data-speak-rate"), 30)
        self.assertIn("classics-speech.js", html)

    def test_sidebar_links_to_classics(self):
        html = self.client.get("/").content.decode()
        self.assertIn('href="/classics/"', html)
