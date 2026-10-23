"""Hostile ZAP-style requests exercise the real email login view."""
from io import StringIO
from urllib.parse import urlencode

from axes.models import AccessAttempt
from django.contrib.auth import BACKEND_SESSION_KEY, get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase

from apps.accounts.forms import LoginForm


class LoginZapTests(TestCase):
    email = "zap-learner@example.test"
    password = "zap-test-password-123"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(cls.email, cls.password)

    def test_repeated_failures_render_lockout_instead_of_server_error(self):
        for attempt in range(8):
            with self.subTest(attempt=attempt + 1):
                response = self.client.post("/accounts/login/", {
                    "username": self.email, "password": "wrong-password",
                })
                self.assertEqual(response.status_code, 200 if attempt < 4 else 429)
                if attempt >= 4:
                    self.assertTemplateUsed(response, "accounts/lockout.html")
                    self.assertContains(response, "Слишком много попыток входа", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_empty_invalid_and_extremely_long_values_are_form_errors(self):
        cases = (
            {},
            {"username": self.email},
            {"password": "wrong-password"},
            {"username": "not-an-email", "password": "wrong-password"},
            {"username": "x" * 10000, "password": "wrong-password"},
            {"username": "x" * 9987 + "@example.test", "password": "wrong-password"},
            {"username": self.email, "password": "x" * 10000},
            {"username": self.email, "password": "wrong-password", "extra": "x" * 10000},
        )
        for index, data in enumerate(cases):
            with self.subTest(case=index):
                response = self.client.post("/accounts/login/", data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_duplicate_username_fields_do_not_crash_or_authenticate(self):
        for names in ((self.email, "not-an-email"), ("not-an-email", self.email),
                      (self.email, ""), ("x" * 10000, self.email)):
            with self.subTest(last_username=names[-1]):
                body = urlencode([("username", name) for name in names] +
                                 [("password", "wrong-password")])
                response = self.client.post("/accounts/login/", body,
                                            content_type="application/x-www-form-urlencoded")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_unsafe_or_malformed_next_is_ignored_after_valid_login(self):
        for target in ("http://evil.com", "//evil.com", "javascript:alert(1)",
                       "http://[", "https:///evil.com", "///evil.com",
                       r"\\evil.com", "http://evil.com/" + "x" * 10000):
            with self.subTest(target=target[:40]):
                client = Client()
                response = client.post("/accounts/login/", {
                    "username": self.email, "password": self.password, "next": target,
                })
                self.assertRedirects(response, "/learning/", fetch_redirect_response=False)
                self.assertEqual(client.session["_auth_user_id"], str(self.user.pk))

    def test_malformed_next_on_failed_login_is_safe_to_render(self):
        for target in ("http://evil.com", "//evil.com", "javascript:alert(1)", "http://["):
            with self.subTest(target=target):
                response = self.client.post("/accounts/login/", {
                    "username": self.email, "password": "wrong-password", "next": target,
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertEqual(response.context["next"], "")

    def test_login_page_next_does_not_create_a_redirect_loop(self):
        response = self.client.post("/accounts/login/", {
            "username": self.email, "password": self.password, "next": "/accounts/login/",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [("/learning/", 302)])

    def test_authenticated_login_post_with_self_next_never_returns_500(self):
        self.client.force_login(self.user)
        response = self.client.post("/accounts/login/", {"next": "/accounts/login/"})
        self.assertRedirects(response, "/learning/", fetch_redirect_response=False)

    def test_missing_csrf_token_is_forbidden_even_with_valid_credentials(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post("/accounts/login/", {
            "username": self.email, "password": self.password,
        })
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("_auth_user_id", client.session)
        self.assertFalse(AccessAttempt.objects.exists())

    def test_signup_uses_model_backend_and_logs_in(self):
        response = self.client.post("/accounts/signup/", {
            "email": "new-zap-learner@example.test", "display_name": "Ученик",
            "password1": self.password, "password2": self.password,
        })
        self.assertRedirects(response, "/learning/", fetch_redirect_response=False)
        self.assertEqual(self.client.session[BACKEND_SESSION_KEY],
                         "django.contrib.auth.backends.ModelBackend")

    def test_axes_reset_allows_login_after_lockout(self):
        for _ in range(6):
            self.client.post("/accounts/login/", {
                "username": self.email, "password": "wrong-password",
            })
        self.assertTrue(AccessAttempt.objects.exists())
        self.assertEqual(self.client.post("/accounts/login/", {
            "username": self.email, "password": self.password,
        }).status_code, 429)
        call_command("axes_reset", stdout=StringIO())
        self.assertFalse(AccessAttempt.objects.exists())
        response = self.client.post("/accounts/login/", {
            "username": self.email, "password": self.password,
        })
        self.assertRedirects(response, "/learning/", fetch_redirect_response=False)

    def test_email_longer_than_model_limit_is_rejected_before_authentication(self):
        # Valid email syntax: total 260 characters, each DNS label below 64.
        email = "a" * 64 + "@" + ".".join(["b" * 63, "c" * 63, "d" * 63]) + ".com"
        self.assertEqual(len(email), 260)
        with self.assertRaises(ValidationError):
            LoginForm().fields["username"].clean(email)
        response = self.client.post("/accounts/login/", {
            "username": email, "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)
        self.assertFalse(AccessAttempt.objects.exists())

    def test_normalized_unicode_email_cannot_exceed_storage_limits(self):
        # U+0130 becomes two code points when lowercased: i + combining dot.
        email = "a" * 64 + "@" + ".".join(["İ" * 23] * 4) + ".com"
        self.assertEqual(len(email), 164)
        self.assertEqual(len(email.lower()), 256)
        response = self.client.post("/accounts/login/", {
            "username": email, "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)
        self.assertFalse(AccessAttempt.objects.exists())

        response = self.client.post("/accounts/signup/", {
            "email": email, "display_name": "Ученик",
            "password1": self.password, "password2": self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(get_user_model().objects.count(), 1)
