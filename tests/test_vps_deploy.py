"""Выкладка на свой сервер (deploy/vps): база не торчит наружу, ключ CI умеет только deploy и backup."""
import os
import shutil
import subprocess
from pathlib import Path
from unittest import skipUnless

import yaml
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]
VPS = ROOT / "deploy" / "vps"


class VpsDeployConfigTests(SimpleTestCase):
    def setUp(self):
        self.compose = yaml.safe_load((VPS / "compose.yml").read_text(encoding="utf-8"))

    def test_database_is_not_published_to_the_internet(self):
        self.assertNotIn("ports", self.compose["services"]["db"])
        self.assertEqual(self.compose["services"]["caddy"]["ports"], ["80:80", "443:443"])

    def test_web_runs_production_settings_with_required_secrets(self):
        env = self.compose["services"]["web"]["environment"]
        self.assertEqual(env["DJANGO_SETTINGS_MODULE"], "config.settings.production")
        self.assertIn(":?", env["DJANGO_SECRET_KEY"])
        self.assertEqual(env["DATABASE_SSLMODE"], "disable")  # только внутренняя сеть Docker
        self.assertIn("healthz", " ".join(self.compose["services"]["web"]["healthcheck"]["test"]))

    def test_server_secrets_never_go_to_git(self):
        ignored = subprocess.run(["git", "check-ignore", "-q", "deploy/vps/.env"], cwd=ROOT, check=False)
        self.assertEqual(ignored.returncode, 0)

    def test_deploy_runs_only_after_green_ci_on_main(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/deploy-vps.yml").read_text(encoding="utf-8"))
        trigger = workflow[True]["workflow_run"]  # PyYAML читает ключ on как True
        self.assertEqual(trigger["workflows"], ["CI"])
        self.assertEqual(trigger["branches"], ["main"])
        self.assertIn("conclusion == 'success'", workflow["jobs"]["deploy"]["if"])


@skipUnless(shutil.which("bash"), "ssh-gate — bash-скрипт сервера")
class SshGateTests(SimpleTestCase):
    def run_gate(self, command):
        env = {**os.environ, "SSH_ORIGINAL_COMMAND": command}
        return subprocess.run(["bash", str(VPS / "ssh-gate.sh")], env=env, capture_output=True, text=True, check=False)

    def test_only_deploy_and_backup_are_allowed(self):
        for command in ("", "bash", "rm -rf /", "deploy; id", "backup && id", "cat /etc/passwd"):
            with self.subTest(command=command):
                result = self.run_gate(command)
                self.assertEqual(result.returncode, 1)
                self.assertIn("не разрешена", result.stderr)
