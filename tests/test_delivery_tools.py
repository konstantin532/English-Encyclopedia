"""Инструменты уровня 4: отчёт о нестабильных тестах и метрики поставки."""

import importlib.util
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclass ищет свой модуль в sys.modules
    spec.loader.exec_module(module)
    return module


def _junit(cases: dict[str, str]) -> str:
    body = []
    for name, outcome in cases.items():
        inner = {"pass": "", "fail": "<failure message='x'/>", "error": "<error message='x'/>", "skip": "<skipped/>"}
        body.append(f"<testcase classname='tests.test_x.T' name='{name}'>{inner[outcome]}</testcase>")
    return f"<testsuites><testsuite>{''.join(body)}</testsuite></testsuites>"


class FlakyReportTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.flaky = _load("flaky_report")

    def run_reports(self, *runs: dict[str, str]):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for index, cases in enumerate(runs):
                path = Path(tmp) / f"run{index}.xml"
                path.write_text(_junit(cases), encoding="utf-8")
                paths.append(str(path))
            output = Path(tmp) / "flaky.md"
            code = self.flaky.main([*paths, "--output", str(output)])
            return code, output.read_text(encoding="utf-8")

    def test_mixed_results_are_flaky_and_constant_failures_are_broken(self):
        code, report = self.run_reports(
            {"test_a": "pass", "test_b": "fail", "test_c": "fail", "test_d": "skip"},
            {"test_a": "pass", "test_b": "pass", "test_c": "error", "test_d": "skip"},
        )
        self.assertEqual(code, 1)
        flaky_part, broken_part = report.split("## Падают во всех прогонах")
        self.assertIn("tests.test_x.T::test_b", flaky_part)
        self.assertIn("tests.test_x.T::test_c", broken_part)
        self.assertNotIn("test_a", report)
        self.assertNotIn("test_d", report)

    def test_stable_runs_exit_zero(self):
        code, report = self.run_reports({"test_a": "pass"}, {"test_a": "pass"})
        self.assertEqual(code, 0)
        self.assertIn("одинаковый результат", report)


class DeliveryMetricsTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.metrics = _load("delivery_metrics")

    def run_payload(self, minutes: int, conclusion: str, event: str = "pull_request", status: str = "completed"):
        start = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        return {
            "status": status,
            "conclusion": conclusion,
            "event": event,
            "run_started_at": start.isoformat().replace("+00:00", "Z"),
            "updated_at": (start + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
        }

    def test_summary_counts_only_finished_pr_runs_and_successful_deploys(self):
        ci = self.metrics.parse_runs(
            {
                "workflow_runs": [
                    self.run_payload(10, "success"),
                    self.run_payload(20, "success"),
                    self.run_payload(30, "failure"),
                    self.run_payload(99, "cancelled"),
                    self.run_payload(5, "success", event="push"),
                    self.run_payload(1, None, status="in_progress"),
                ]
            }
        )
        deploys = self.metrics.parse_runs(
            {
                "workflow_runs": [self.run_payload(3, "success", event="workflow_run")] * 4
                + [self.run_payload(3, "failure")]
            }
        )
        summary = self.metrics.summarize(ci, deploys, days=28)
        self.assertEqual(summary["ci_runs"], 3)
        self.assertEqual(summary["ci_median_minutes"], 20.0)
        self.assertEqual(summary["ci_success_rate"], 0.667)
        self.assertEqual(summary["deploys"], 4)
        self.assertEqual(summary["deploys_per_week"], 1.0)
        self.assertIn("| CI, медиана | 20.0 мин |", self.metrics.render(summary))

    def test_empty_history_is_reported_honestly(self):
        report = self.metrics.render(self.metrics.summarize([], [], days=30))
        self.assertIn("нет данных", report)


class Level4WorkflowTests(SimpleTestCase):
    def workflow(self, name):
        return yaml.load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    def test_flaky_workflow_compares_several_shuffled_runs(self):
        workflow = self.workflow("flaky-tests.yml")
        self.assertGreaterEqual(len(workflow["jobs"]["shuffled"]["strategy"]["matrix"]["run"]), 3)
        text = (ROOT / ".github" / "workflows" / "flaky-tests.yml").read_text(encoding="utf-8")
        self.assertIn("--randomly-seed", text)
        self.assertIn("flaky_report.py", text)

    def test_deploy_marks_release_without_failing_the_deploy(self):
        text = (ROOT / ".github" / "workflows" / "deploy-vps.yml").read_text(encoding="utf-8")
        self.assertIn('"$api/$RELEASE/deploys/"', text)
        self.assertIn("Sentry не подключён", text)
