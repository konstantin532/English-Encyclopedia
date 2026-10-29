"""CEFR word-level matches are not certifications of senses."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from django.test import SimpleTestCase
from scripts.audit_cefr_evidence import inspect

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("oxford_check", ROOT / "scripts/check_cefr_oxford3000.py")
oxford = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oxford)


class CEFRIntegrityTests(SimpleTestCase):
    def test_real_a1_corpus_can_be_audited_without_certifying_it(self):
        report = inspect()
        self.assertEqual(report["counts"]["total"], 516)
        self.assertFalse(report["errors"], report["errors"])
        self.assertEqual(report["counts"].get("status_verified", 0) +
                         report["counts"].get("status_partial", 0) +
                         report["counts"].get("status_pending", 0), 516)

    def test_verified_requires_specific_evidence_not_word_level_only(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / "content/seed_lexicon"
            directory.mkdir(parents=True)
            (directory / "one.yaml").write_text(yaml.safe_dump({"level": "A1", "units": [
                {"uid":"LX-00001", "lemma":"bank", "meaning":"river edge", "class":"S2",
                 "cefr":"A1", "verification_status":"verified",
                 "verification_note":"Oxford 3000; значение отдельно не сверялось"},
                {"uid":"LX-00002", "lemma":"bank", "meaning":"financial institution", "class":"S2",
                 "cefr":"A1", "verification_status":"partial",
                 "verification_note":"word-level Oxford lemma/POS only"},
            ]}, allow_unicode=True), encoding="utf-8")
            report = inspect(Path(tmp))
            self.assertEqual(report["counts"]["total"], 2)
            self.assertEqual(len(report["errors"]), 1)
            self.assertEqual(report["documented_sense_claims"], 0)

    def test_oxford_pos_matches_do_not_match_substrings(self):
        self.assertFalse(oxford.matches_category("some pron. A1", "S"))
        self.assertTrue(oxford.matches_category("some pron. A1", "T"))
        self.assertTrue(oxford.matches_category("family n., adj. A1", "S"))
        self.assertIsNone(oxford.unambiguous_hit([("A1","bank n. A1"), ("B2","bank n. B2")], "S"))


    def test_untraceable_verified_claims_are_rejected_even_with_confident_notes(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / "content/seed_lexicon"
            directory.mkdir(parents=True)
            base = {
                "uid": "LX-00001", "lemma": "eat", "meaning": "to consume food", "class": "D2",
                "cefr": "A1", "verification_status": "verified",
                "verification_sense": "eat verb (FOOD)",
                "verification_note": "Cambridge English Dictionary, eat verb (FOOD), A1",
            }
            valid_url = "https://dictionary.cambridge.org/us/dictionary/english/eat"
            broken = [
                {**base},  # unverifiable assertion with no URL
                {**base, "verification_source_url":
                    "https://dictionary.cambridge.org.evil.example/us/dictionary/english/eat"},
                {**base, "verification_source_url":
                    "https://dictionary.cambridge.org/us/dictionary/english/cat"},
                {**base, "verification_source_url": valid_url,
                    "verification_sense": "eat verb (DIFFERENT SENSE)"},
                {**base, "verification_source_url": valid_url,
                    "verification_note": "Cambridge English Dictionary, eat verb (FOOD), B2"},
            ]
            for row in broken:
                with self.subTest(row=row):
                    (directory / "one.yaml").write_text(
                        yaml.safe_dump({"level": "A1", "units": [row]},
                                       allow_unicode=True), encoding="utf-8"
                    )
                    report = inspect(Path(tmp))
                    self.assertEqual(len(report["errors"]), 1, report)
                    self.assertEqual(report["documented_sense_claims"], 0)
            (directory / "one.yaml").write_text(
                yaml.safe_dump({"level": "A1", "units": [
                    {**base, "verification_source_url": valid_url}
                ]}, allow_unicode=True), encoding="utf-8"
            )
            self.assertEqual(inspect(Path(tmp))["errors"], [])
