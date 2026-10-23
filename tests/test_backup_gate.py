"""The scheduled database backup must fail closed if required secrets are absent.

These tests execute only the configuration gate; they never contact a database
or attempt to dump production data.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import skipUnless

import yaml
from django.test import SimpleTestCase


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/backup.yml"


@skipUnless(shutil.which("bash"), "Backup gate runs in the Ubuntu GitHub Actions shell")
class BackupGateTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        steps = workflow["jobs"]["backup"]["steps"]
        cls.gate = next(step["run"] for step in steps if step.get("id") == "check")

    def run_gate(self, url, passphrase, vps=("", "", "")):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "github-output.txt"
            env = {
                **os.environ,
                "BACKUP_DATABASE_URL": url,
                "BACKUP_PASSPHRASE": passphrase,
                "VPS_HOST": vps[0],
                "VPS_SSH_KEY": vps[1],
                "VPS_KNOWN_HOSTS": vps[2],
                "GITHUB_OUTPUT": str(output),
            }
            result = subprocess.run(
                ["bash", "-e", "-c", self.gate],
                text=True, capture_output=True, env=env, check=False,
            )
            written = output.read_text(encoding="utf-8") if output.exists() else ""
            return result, written

    def test_missing_backup_secret_fails_the_workflow_gate(self):
        for url, passphrase in (
            ("", ""),
            ("", "dummy-non-production-key"),
            ("postgres://example.invalid/db", ""),
        ):
            with self.subTest(url_is_set=bool(url), passphrase_is_set=bool(passphrase)):
                process, written = self.run_gate(url, passphrase)
                self.assertNotEqual(process.returncode, 0)
                self.assertIn("::error::", process.stdout)
                self.assertNotIn("configured=true", written)

    def test_both_backup_secrets_allow_the_gate(self):
        process, written = self.run_gate(
            "postgres://example.invalid/db", "dummy-non-production-key",
        )
        self.assertEqual(process.returncode, 0)
        self.assertIn("configured=true", written)

    def test_own_server_is_a_backup_source(self):
        vps = ("203.0.113.5", "dummy-key", "203.0.113.5 ssh-ed25519 AAAA")
        process, written = self.run_gate("", "dummy-non-production-key", vps)
        self.assertEqual(process.returncode, 0)
        self.assertIn("configured=true", written)
        self.assertIn("mode=vps", written)

    def test_partial_server_secrets_do_not_count(self):
        process, written = self.run_gate("", "dummy-non-production-key", ("203.0.113.5", "", ""))
        self.assertNotEqual(process.returncode, 0)
        self.assertNotIn("configured=true", written)

    def test_server_without_passphrase_fails(self):
        vps = ("203.0.113.5", "dummy-key", "203.0.113.5 ssh-ed25519 AAAA")
        process, written = self.run_gate("", "", vps)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("::error::", process.stdout)
