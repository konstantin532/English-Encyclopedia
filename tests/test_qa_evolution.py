"""Quality framework contracts and behavioral tests used by mutation probes."""
from django.test import SimpleTestCase

from apps.drills.models import Exercise
import scripts.qa_evolution as qa
from scripts.qa_evolution import fuzz_budget, make_quality_report


class ProgressiveQualityTests(SimpleTestCase):
    def test_fuzz_budgets_increase_and_have_limits(self):
        self.assertLess(fuzz_budget(1)[0], fuzz_budget(20)[0])
        self.assertLess(fuzz_budget(1)[1], fuzz_budget(50)[1])
        self.assertEqual(fuzz_budget(1000000), (1200, 120))
        self.assertEqual(fuzz_budget(1000000, deep=True), (6000, 120))

    def test_quality_gate_flags_regressions(self):
        coverage = {"totals": {"percent_covered": 69}, "files": {}}
        baseline = {"minimum_coverage_percent": 70, "minimum_test_cases": 100}
        report, failures = make_quality_report(coverage, 99, baseline)
        self.assertEqual(len(failures), 2)
        self.assertIn("69.00%", report)

    def test_quality_gate_accepts_floor(self):
        coverage = {"totals": {"percent_covered": 70}, "files": {}}
        baseline = {"minimum_coverage_percent": 70, "minimum_test_cases": 100}
        self.assertEqual(make_quality_report(coverage, 100, baseline)[1], [])

    def test_normalize_curly_apostrophe(self):
        self.assertEqual(Exercise.normalize(" It’s "), "it's")

    def test_normalize_trailing_punctuation(self):
        self.assertEqual(Exercise.normalize(" Hello!? "), "hello")

    def test_exercise_accepts_alternative_answers(self):
        exercise = Exercise(answer="thanks", accepted=["thank you"])
        self.assertTrue(exercise.is_correct("Thank you."))


class FuzzRegressionTests(SimpleTestCase):
    """Контрпример из GitHub Actions (PR situation-weeks → main): слово из одного пробела."""

    def test_counterexample_seed_from_pull_request(self):
        qa.run_fuzz(38811173329, 6)

    def test_blank_marker_is_reported_not_accepted(self):
        from apps.taxonomy.markup import find_issues

        self.assertTrue(find_issues("[S1] [/]"))
