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
        self.assertEqual(report["counts"]["total"], 500)
        self.assertFalse(report["errors"], report["errors"])
        self.assertEqual(report["counts"].get("status_verified", 0) +
                         report["counts"].get("status_partial", 0) +
                         report["counts"].get("status_pending", 0), 500)

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
