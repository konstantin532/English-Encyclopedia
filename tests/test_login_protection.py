"""Fast integration checks for the real email login endpoint."""
from datetime import timedelta
from unittest.mock import patch

from axes.models import AccessAttempt

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone


class LoginProtectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            "learner@example.com", "login-test-password-123",
        )

    def login(self, password, **extra):
        return self.client.post("/accounts/login/", {
            "username": self.user.email, "password": password,
        }, **extra)

    def test_five_failures_block_even_correct_password_without_hashing(self):
        for _ in range(5):
            self.login("wrong-password")
        with patch.object(get_user_model(), "check_password") as check_password:
            response = self.login("login-test-password-123")
        self.assertContains(response, "Слишком много попыток входа", status_code=429)
        check_password.assert_not_called()
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.get("/learning/"),
                             "/accounts/login/?next=/learning/", fetch_redirect_response=False)

    def test_correct_password_before_limit_still_logs_in(self):
        for _ in range(4):
            self.login("wrong-password")
        response = self.login("login-test-password-123")
        self.assertRedirects(response, "/learning/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_attempts_use_normalized_email(self):
        self.client.post("/accounts/login/", {
            "username": "LEARNER@EXAMPLE.COM", "password": "wrong-password",
        })
        attempt = AccessAttempt.objects.get()
        self.assertEqual(attempt.username, self.user.email)
        self.assertEqual(attempt.ip_address, "127.0.0.1")
        self.assertEqual(attempt.failures_since_start, 1)

    def test_lockout_is_limited_to_email_and_ip_pair(self):
        for _ in range(5):
            self.login("wrong-password")
        other = get_user_model().objects.create_user(
            "other@example.com", "other-login-password-123",
        )
        response = Client().post("/accounts/login/", {
            "username": other.email, "password": "other-login-password-123",
        })
        self.assertRedirects(response, "/learning/", fetch_redirect_response=False)
        response = self.login("login-test-password-123", REMOTE_ADDR="192.0.2.1")
        self.assertRedirects(response, "/learning/", fetch_redirect_response=False)
        # A success from another IP must not clear the original pair's lockout.
        self.client.logout()
        self.assertEqual(self.login("login-test-password-123").status_code, 429)

    def test_success_resets_failure_count(self):
        for _ in range(4):
            self.login("wrong-password")
        self.assertEqual(self.login("login-test-password-123").status_code, 302)
        self.assertFalse(AccessAttempt.objects.exists())
        self.client.logout()
        for _ in range(4):
            self.assertEqual(self.login("wrong-password").status_code, 200)
        self.assertEqual(self.login("login-test-password-123").status_code, 302)

    def test_lockout_expires_after_thirty_minutes(self):
        for _ in range(5):
            self.login("wrong-password")
        AccessAttempt.objects.update(attempt_time=timezone.now() - timedelta(minutes=29))
        self.assertEqual(self.login("login-test-password-123").status_code, 429)
        AccessAttempt.objects.update(attempt_time=timezone.now() - timedelta(minutes=31))
        response = self.login("login-test-password-123")
        self.assertRedirects(response, "/learning/", fetch_redirect_response=False)
