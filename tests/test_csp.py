"""Exercise the actual production policy with the isolated test database."""
import os
import re
import runpy
from unittest.mock import patch

from django.test import Client, SimpleTestCase, TestCase, override_settings

from config.settings import base


def production_security(report_only=False):
    # Import the real production module without connecting to production or
    # weakening its PostgreSQL/secret requirements in application code.
    with (
        patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "DJANGO_CSP_REPORT_ONLY": "1" if report_only else "0",
        }),
        patch.object(base, "DATABASES", {"default": {"ENGINE": "django.db.backends.postgresql"}}),
        patch.object(base, "SECRET_KEY", "production-settings-test-only-key"),
    ):
        production = runpy.run_module("config.settings.production")
    return {
        "DEBUG": False,
        "MIDDLEWARE": production["MIDDLEWARE"],
        "CONTENT_SECURITY_POLICY": production.get("CONTENT_SECURITY_POLICY"),
        "CONTENT_SECURITY_POLICY_REPORT_ONLY": production.get("CONTENT_SECURITY_POLICY_REPORT_ONLY"),
    }


class CSPTests(SimpleTestCase):
    def test_local_and_test_settings_do_not_enforce_csp(self):
        response = self.client.get("/accounts/login/")
        self.assertNotIn("Content-Security-Policy", response)
        self.assertNotIn("Content-Security-Policy-Report-Only", response)

    def test_production_header_matches_policy_and_two_synchronous_nonce_scripts(self):
        with override_settings(**production_security()):
            first = Client().get("/accounts/login/")
            second = Client().get("/accounts/login/")
        header = first["Content-Security-Policy"]
        directives = dict(part.strip().split(" ", 1) for part in header.split(";") if part.strip())
        expected = {
            "default-src": "'self'", "style-src": "'self' 'unsafe-inline'",
            "img-src": "'self' data:", "font-src": "'self'", "media-src": "'self' blob:",
            "connect-src": "'self'", "object-src": "'none'", "base-uri": "'self'",
            "form-action": "'self'", "frame-ancestors": "'none'",
        }
        for name, value in expected.items():
            self.assertEqual(directives[name], value)
        html = first.content.decode()
        inline = re.findall(r'<script([^>]*)>(.*?)</script>', html, re.S)
        inline = [(attrs, body) for attrs, body in inline if "src=" not in attrs]
        self.assertEqual(len(inline), 2)
        nonces = [re.search(r'nonce="([^"]+)"', attrs).group(1) for attrs, _ in inline]
        self.assertEqual(nonces[0], nonces[1])
        self.assertEqual(directives["script-src"], "'self' 'nonce-" + nonces[0] + "'")
        self.assertNotIn("Content-Security-Policy-Report-Only", first)
        for attrs, body in inline:
            self.assertNotIn("defer", attrs)
            self.assertNotIn("async", attrs)
            self.assertIn(body, html.split("</head>")[0])
        self.assertIn("ee-motion-mode", inline[0][1])
        self.assertIn("ee-markers", inline[1][1])
        second_nonce = re.search(r"'nonce-([^']+)'", second["Content-Security-Policy"]).group(1)
        self.assertNotEqual(nonces[0], second_nonce)

    def test_environment_selects_report_only_without_enforcement(self):
        with override_settings(**production_security(report_only=True)):
            response = Client().get("/accounts/login/")
        self.assertNotIn("Content-Security-Policy", response)
        header = response["Content-Security-Policy-Report-Only"]
        self.assertIn("script-src 'self' 'nonce-", header)
        self.assertNotIn("'unsafe-inline'", header.split("script-src ")[1].split(";")[0])

    def test_error_responses_still_have_production_policy(self):
        with override_settings(**production_security(), ROOT_URLCONF="tests.test_error_pages"):
            client = Client(raise_request_exception=False)
            for url, status in (("/missing/", 404), ("/broken/", 500)):
                with self.subTest(url=url):
                    response = client.get(url)
                    self.assertEqual(response.status_code, status)
                    self.assertIn("Content-Security-Policy", response)
                    self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])


class CSPLockoutTests(TestCase):
    def test_axes_lockout_template_can_generate_nonce_before_header_is_written(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user("csp-lockout@example.test", "correct-password-123")
        with override_settings(**production_security()):
            client = Client()
            for _ in range(6):
                response = client.post("/accounts/login/", {"username": user.email, "password": "wrong"})
            self.assertContains(response, "Слишком много попыток входа", status_code=429)
            header = response["Content-Security-Policy"]
            nonce = re.search(r"'nonce-([^']+)'", header).group(1)
            self.assertContains(response, 'nonce="' + nonce + '"', status_code=429)
