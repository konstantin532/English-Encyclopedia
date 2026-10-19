"""Evidence-driven A1 editorial regression checks.

These checks catch known bilingual/semantic regressions; passing them is not
human CEFR, translation, pronunciation or pedagogy certification.
"""
import json
import re
from pathlib import Path

import yaml
from django.conf import settings
from django.test import SimpleTestCase

from scripts.audit_cefr_evidence import inspect as audit_cefr

ROOT = Path(settings.BASE_DIR)
CONTENT = ROOT / "content"
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


def tagged_to_plain(text):
    return re.sub(r"\[[^\]]+\]", "", text)


def lexicon():
    files = sorted((CONTENT / "seed_lexicon").glob("a1_*.yaml"))
    entries = []
    for path in files:
        pack = yaml.safe_load(path.read_text(encoding="utf-8"))
        if pack.get("level") == "A1":
            entries.extend(pack["units"])
    return entries


class A1LinguisticIntegrityTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.units = lexicon()
        cls.by_id = {u["uid"]: u for u in cls.units}

    def test_full_a1_material_inventory_and_unique_ids(self):
        self.assertEqual(len(self.units), 500)
        self.assertEqual(set(self.by_id), {f"LX-{n:05d}" for n in range(1, 501)})
        self.assertEqual(len(list((CONTENT / "seed_weeks").glob("a1_w*.yaml"))), 14)
        lesson_files = sorted((CONTENT / "seed_lessons").glob("a1_w*.yaml"))
        self.assertEqual(len(lesson_files), 28)
        self.assertEqual(
            sorted(yaml.safe_load(p.read_text(encoding="utf-8"))["order"] for p in lesson_files),
            list(range(1, 29)),
        )
        for path in lesson_files:
            lesson = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual([x["number"] for x in lesson["layers"]], list(range(1, 8)), path.name)
            self.assertFalse(set(lesson.get("units", [])) - set(self.by_id), path.name)
        self.assertEqual(len(list((CONTENT / "seed_stories").glob("s0[1-5]_*.yaml"))), 5)
        self.assertEqual(len(list((CONTENT / "seed_poems").glob("p0[1-7]_*.yaml"))), 7)
        scenario_files = sorted((CONTENT / "active_a1").glob("scenarios_*.json"))
        scenarios = [s for p in scenario_files for s in json.loads(p.read_text(encoding="utf-8"))]
        self.assertEqual(sorted(s["n"] for s in scenarios), list(range(1, 29)))

    def test_500_entries_have_usable_bilingual_identity_and_honest_cefr(self):
        for entry in self.units:
            with self.subTest(uid=entry["uid"]):
                for key in ("lemma", "meaning", "translation_ru", "ipa_us", "example_en", "example_ru"):
                    self.assertTrue(str(entry.get(key, "")).strip(), key)
                self.assertIn(entry.get("verification_status", "pending"),
                              ("pending", "partial", "verified"))
                if entry.get("verification_status") == "verified":
                    self.assertNotEqual(entry.get("cefr"), "unverified")
                    self.assertTrue(entry.get("verification_note", "").strip())
        result = audit_cefr(ROOT)
        self.assertEqual(result["counts"]["total"], 500)
        self.assertEqual(result["errors"], [])

    def test_some_is_not_taught_as_necessarily_a_small_amount(self):
        some = self.by_id["LX-00113"]
        self.assertIn("точное число не названо", some["translation_ru"])
        self.assertIn("не означает обязательно маленькую порцию", some["usage_note"])
        lesson = yaml.safe_load(
            (CONTENT / "seed_lessons/a1_w05_l09_there_is.yaml").read_text(encoding="utf-8")
        )
        self.assertIn("без точного количества", lesson["summary"])
        self.assertIn("не обязательно мало", str(lesson["exercises"]))

    def test_dictionary_examples_do_not_change_the_proposition(self):
        eat = self.by_id["LX-00303"]
        self.assertEqual(eat["example_ru"], "Я ем в двенадцать.")
        self.assertIn("eat", tagged_to_plain(eat["example_en"]))
        self.assertEqual(self.by_id["LX-00309"]["example_ru"], "Я обедаю в двенадцать.")
        self.assertEqual(tagged_to_plain(self.by_id["LX-00350"]["example_en"]),
                         "Which phone is new?")
        self.assertEqual(self.by_id["LX-00350"]["example_ru"], "Какой телефон новый?")
        self.assertIn("Мужчина этажом выше", self.by_id["LX-00148"]["example_ru"])
        self.assertIn("Парк-стрит", self.by_id["LX-00418"]["example_ru"])
        self.assertIn("апельсиновый (о соке)", self.by_id["LX-00292"]["translation_ru"])
        self.assertEqual(tagged_to_plain(self.by_id["LX-00449"]["example_en"]),
                         "Open your book to page ten.")
        self.assertEqual(tagged_to_plain(self.by_id["LX-00337"]["example_en"]),
                         "The key is under the table.")

    def test_recurring_days_are_explicit_and_forms_registered(self):
        sat = self.by_id["LX-00194"]
        sun = self.by_id["LX-00195"]
        self.assertIn("Saturdays", sat["forms"])
        self.assertIn("Sundays", sun["forms"])
        for day in DAYS:
            unit = next(u for u in self.units if u["lemma"] == day)
            with self.subTest(day=day):
                self.assertIn(day + "s", unit["forms"])
                self.assertIn("on " + day + "s", tagged_to_plain(unit["example_en"]))
        self.assertIn("on Saturdays", self.by_id["LX-00207"]["lemma"])
        self.assertIn("ˌdeɪz", self.by_id["LX-00207"]["ipa_us"])
        week = yaml.safe_load(
            (CONTENT / "seed_weeks/a1_w10.yaml").read_text(encoding="utf-8")
        )
        dialogue = "\n".join(tagged_to_plain(row["text"]) for row in week["script"])
        self.assertIn("I always read on Saturdays.", dialogue)
        self.assertIn("I play the guitar on Sundays.", dialogue)
        self.assertIn("I work on Sundays.", dialogue)
        topics = json.loads(
            (CONTENT / "active_a1/topics_19_20.json").read_text(encoding="utf-8")
        )
        self.assertEqual(topics[0]["answer"], "I always read on Saturdays.")
        scenarios = json.loads(
            (CONTENT / "active_a1/scenarios_19_20.json").read_text(encoding="utf-8")
        )
        self.assertIn("on Saturdays", scenarios[0]["missions"][0]["example"])
        self.assertIn("on Mondays", scenarios[0]["missions"][3]["example"])

    def test_poem_generator_and_poem_agree_on_temporal_on_and_plural_ipa(self):
        poem = yaml.safe_load(
            (CONTENT / "seed_poems/p05_read_walk_play.yaml").read_text(encoding="utf-8")
        )
        self.assertIn("[P3]on[/] [S7]Saturdays[/]", poem["body"])
        self.assertIn("[P3]on[/] [S7]Sundays[/]", poem["body"])
        self.assertNotIn("[P1]on[/]", poem["body"])
        pronunciations = " ".join(part["ipa"] for part in poem["pronunciation"])
        self.assertIn("ˈsæt̬ɚˌdeɪz", pronunciations)
        self.assertIn("ˈsʌnˌdeɪz", pronunciations)
        generator = (ROOT / "scripts/build_poems.py").read_text(encoding="utf-8")
        self.assertIn("on|P3 Saturdays.", generator)
        self.assertIn("on|P3 Sundays.", generator)
