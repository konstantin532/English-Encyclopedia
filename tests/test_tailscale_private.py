"""Static safety rails for the optional Tailscale-only Windows launcher.

These checks do not replace real Windows/Android connectivity testing.
"""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class TailscalePrivateLauncherTests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)
        self.script = (root / "scripts" / "start_tailscale_private.ps1").read_text(encoding="utf-8")
        self.batch = (root / "start_tailscale_private.bat").read_text(encoding="utf-8")
        self.ignore = (root / ".gitignore").read_text(encoding="utf-8")
        self.docs = (root / "docs" / "operations" / "TAILSCALE_PRIVATE.md").read_text(encoding="utf-8")

    def test_uses_secure_wsgi_only_on_loopback(self):
        self.assertIn('config.settings.production', self.script)
        self.assertIn('$env:DJANGO_DEBUG = "false"', self.script)
        self.assertIn('$env:DJANGO_SECURE_SSL_REDIRECT = "true"', self.script)
        self.assertIn("--listen=127.0.0.1:8000", self.script)
        self.assertIn("--url-scheme=https", self.script)
        self.assertIn("config.wsgi:application", self.script)
        self.assertNotIn("--listen=0.0.0.0", self.script)
        self.assertNotIn("manage.py runserver", self.script)
        self.assertNotIn("tailscale funnel --bg", self.script)

    def test_django_hosts_csrf_and_permanent_secret_are_configured(self):
        for required in ("DJANGO_ALLOWED_HOSTS", "DJANGO_CSRF_TRUSTED_ORIGINS",
                         "DJANGO_SECRET_KEY", "DJANGO_SETTINGS_MODULE",
                         "UTF8Encoding", "RandomNumberGenerator"):
            self.assertIn(required, self.script)
        self.assertIn(".env", self.ignore)
        self.assertIn("db.sqlite3", self.ignore)

    def test_launcher_and_docs_emphasize_private_access(self):
        self.assertIn("start_tailscale_private.ps1", self.batch)
        self.assertIn("tailscale serve --bg 8000", self.docs)
        self.assertIn("tailscale serve off", self.docs)
        self.assertIn("Tailscale Serve", self.docs)
        self.assertIn("main", self.docs)
        self.assertIn("situation-weeks", self.docs)
