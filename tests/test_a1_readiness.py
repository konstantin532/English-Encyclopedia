"""Safety rails for the A1-to-A1+ foundation report.

These checks are intentionally separate from tests of student proficiency.
"""
from tempfile import TemporaryDirectory
from pathlib import Path

from django.test import SimpleTestCase

from scripts.a1_readiness import EXPECTED, audit, markdown


class A1FoundationReportTests(SimpleTestCase):
    def test_a1_materials_reach_structural_targets(self):
        report = audit()
        self.assertTrue(report["structural_pass"], report["checks"])
        for key in ("weeks", "lessons", "units", "stories", "poems",
                    "twisters", "missions", "twists"):
            self.assertEqual(report["counts"][key], EXPECTED[key], key)
        self.assertEqual(len(report["weekly_units"]), 14)

    def test_verified_cefr_is_not_confused_with_suggested_cefr(self):
        report = audit()
        self.assertEqual(
            report["counts"]["cefr_verified_units"]
            + report["counts"]["cefr_not_fully_verified_units"],
            report["counts"]["units"],
        )
        self.assertIn("NOT CERTIFIED", report["a1_plus_gate"])
        self.assertIn("independent_spoken_and_listening_pilot",
                      report["independent_evidence"])
        self.assertIn("не выдаёт сертификат", markdown(report))

    def test_missing_materials_fail_closed_without_claiming_learning_success(self):
        with TemporaryDirectory() as temp:
            report = audit(Path(temp))
        self.assertFalse(report["structural_pass"])
        self.assertFalse(report["checks"]["units"])
        self.assertFalse(report["checks"]["lessons"])
        self.assertEqual(report["counts"]["cefr_verified_units"], 0)
        self.assertIn("FAIL", markdown(report))
