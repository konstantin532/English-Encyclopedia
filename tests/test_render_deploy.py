"""Render and Django production readiness checks without external services."""
from pathlib import Path
from unittest import mock

import yaml
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse

ROOT = Path(__file__).resolve().parents[1]


class RenderContractTests(TestCase):
    def test_health_endpoint_returns_db_status_and_never_cache(self):
        response = self.client.get(reverse("core:healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status":"ok"})
        self.assertIn("no-cache", response.headers["Cache-Control"])

    def test_health_endpoint_signals_database_failure(self):
        from apps.core import views
        with mock.patch.object(views.connections["default"], "cursor", side_effect=DatabaseError("secret")):
            response = self.client.get(reverse("core:healthz"))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"secret", response.content)

    def test_blueprint_requires_external_secret_and_durable_postgres(self):
        data = yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8"))
        service = data["services"][0]
        self.assertEqual(service["healthCheckPath"], "/healthz/")
        self.assertEqual(service["runtime"], "python")
        env = {item["key"]: item for item in service["envVars"]}
        self.assertTrue(env["DJANGO_SECRET_KEY"]["generateValue"])
        self.assertFalse(env["DATABASE_URL"]["sync"])
        self.assertEqual(env["DJANGO_SETTINGS_MODULE"]["value"], "config.settings.production")
        start = (ROOT / "deploy/render-start.sh").read_text(encoding="utf-8")
        self.assertIn("migrate --noinput", start)
        self.assertIn("gunicorn config.wsgi:application", start)
        self.assertNotIn("runserver", start)
