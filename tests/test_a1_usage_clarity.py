"""A1 regression checks for learner-facing semantic and morphology explanations.

These assertions protect selected verified examples, not a full human review
of American English usage or the A1 curriculum.
"""
from pathlib import Path

import yaml
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.taxonomy.registry import CATEGORY_BY_CODE
from tests.runner import ensure_content


ROOT = Path(__file__).resolve().parent.parent
LEXICON = ROOT / "content" / "seed_lexicon"


def units_in(filename):
    data = yaml.safe_load((LEXICON / filename).read_text(encoding="utf-8"))
    return {unit["lemma"]: unit for unit in data["units"]}


class A1UsageMetadataTests(SimpleTestCase):
    def test_verb_semantic_class_is_independent_from_inflection(self):
        units = units_in("a1_w06_day.yaml")
        self.assertEqual(units["go"]["class"], "D4")
        self.assertIn("irregular", units["go"]["grammar_features"])
        self.assertIn("went", units["go"]["forms"])
        self.assertEqual(units["work"]["class"], "D2")
        self.assertIn("regular", units["work"]["grammar_features"])
        self.assertIn("worked", units["work"]["forms"])
        self.assertEqual(len(CATEGORY_BY_CODE["D"].classes), 10)

        eat = units_in("a1_w06_day_plus.yaml")["eat"]
        self.assertEqual(eat["class"], "D2")
        self.assertIn("irregular", eat["grammar_features"])
        self.assertIn("ate", eat["forms"])

    def test_home_notes_do_not_invent_indoor_outdoor_rule(self):
        home = units_in("a1_w01_nouns.yaml")["home"]
        self.assertIn("I'm home и I'm at home", home["usage_note"])
        self.assertIn("могут просто означать", home["usage_note"])
        at = units_in("a1_w01_core.yaml")["at"]
        self.assertIn("оба могут означать", at["usage_note"])
        lesson = yaml.safe_load(
            (ROOT / "content" / "seed_lessons" / "a1_w01_l02_be.yaml").read_text(encoding="utf-8")
        )
        layer_6 = next(layer["body"] for layer in lesson["layers"] if layer["number"] == 6)
        self.assertIn("Можно ли поменять варианты местами?", layer_6)
        self.assertIn("внутри здания или рядом", layer_6)


class LexiconExplanationPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_dictionary_explains_class_and_separate_verb_morphology(self):
        cases = (
            ("LX-00016", "Неправильный глагол", "D1"),
            ("LX-00127", "Неправильный глагол", "D4"),
            ("LX-00128", "Правильный глагол", "D2"),
            ("LX-00035", "Модальный глагол", "D7"),
        )
        for uid, morphology, class_id in cases:
            with self.subTest(uid=uid):
                response = self.client.get(reverse("lexicon:detail", args=[uid]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, morphology)
                self.assertContains(response, class_id)
                self.assertContains(response, "Как работают цвета и линии")
                self.assertContains(response, "не признак правильного или неправильного глагола")

    def test_home_usage_note_is_visible_in_dictionary(self):
        response = self.client.get(reverse("lexicon:detail", args=["LX-00005"]))
        self.assertContains(response, "I'm home и I'm at home")
        self.assertContains(response, "могут просто означать")
