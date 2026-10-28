"""Week-one dialogue prerequisites and vocabulary, without loading the course DB."""
from pathlib import Path
from types import SimpleNamespace

import yaml
from django.test import SimpleTestCase

from apps.publishing.audit import is_known, text_tokens, unit_words
from apps.taxonomy.markup import find_issues, strip_markup


CONTENT = Path(__file__).resolve().parents[1] / "content"


def read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class WeekOneDialogueTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.scene = read_yaml(CONTENT / "seed_weeks/a1_w01.yaml")
        cls.voices = read_yaml(CONTENT / "manifests/voices.yaml")
        cls.vocab = {
            item["name"].lower()
            for item in read_yaml(CONTENT / "manifests/characters.yaml")["characters"]
        }
        for path in (CONTENT / "seed_lexicon").glob("*.yaml"):
            data = read_yaml(path)
            if data.get("level") == "A1" and data.get("week", 99) <= 1:
                for unit in data["units"]:
                    cls.vocab |= unit_words(SimpleNamespace(
                        lemma=unit["lemma"], forms=unit.get("forms", []),
                        unit_type=unit.get("unit_type", "word"),
                    ))

    def test_both_modes_use_only_week_one_vocabulary(self):
        for index, line in enumerate(self.scene["script"]):
            for mode in ("text", "spoken"):
                with self.subTest(line=index + 1, mode=mode):
                    tokens = text_tokens(line.get(mode, line["text"]))
                    self.assertTrue(tokens)
                    self.assertEqual(
                        sorted({word for word in tokens if not is_known(word, self.vocab)}),
                        [],
                    )

    def test_later_words_are_not_accidentally_allowed(self):
        for word in ("thanks", "cat", "tomorrow"):
            with self.subTest(word=word):
                self.assertFalse(is_known(word, self.vocab))

    def test_negative_be_is_explained_in_the_week_one_lesson(self):
        lesson = read_yaml(CONTENT / "seed_lessons/a1_w01_l02_be.yaml")
        body = "\n".join(strip_markup(layer["body"]) for layer in lesson["layers"])
        self.assertIn("I am not busy", body)
        self.assertIn("I'm not busy", body)

    def test_hesitation_is_supported_by_the_audio_configuration(self):
        hesitation = self.voices["emotions"].get("hesitant")
        self.assertIsNotNone(hesitation, "The selected dialogue needs a supported hesitation profile")
        self.assertEqual(hesitation["name_ru"], "нерешительно")
        self.assertGreater(hesitation["pause"], self.voices["emotions"]["neutral"]["pause"])
        lines = [line for line in self.scene["script"] if line.get("emotion") == "hesitant"]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["speaker"], "tom")

    def test_roles_emotions_and_markup_are_valid(self):
        for line in self.scene["script"]:
            self.assertIn(line["speaker"], self.voices["roles"])
            self.assertIn(line.get("emotion", "neutral"), self.voices["emotions"])
            for mode in ("text", "spoken"):
                with self.subTest(speaker=line["speaker"], mode=mode):
                    self.assertEqual(find_issues(line.get(mode, line["text"])), [])

    def test_spoken_contractions_have_corresponding_full_forms(self):
        pairs = (("What is", "What's"), ("My name is", "My name's"),
                 ("I am", "I'm"), ("It is", "It's"))
        for line in self.scene["script"]:
            full = strip_markup(line["text"])
            for long, short in pairs:
                if long in full:
                    with self.subTest(full=full, contraction=short):
                        self.assertIn(short, strip_markup(line.get("spoken", "")))
