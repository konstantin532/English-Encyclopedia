"""Bounded retry policy, without database or timing dependencies."""
from contextlib import nullcontext
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

from django.db import OperationalError
from django.test import SimpleTestCase, RequestFactory

from apps.learning.request_serialization import serialized_learning_post


class RetryPolicyTests(SimpleTestCase):
    def exercise(self, code, *, outer=False, vendor='sqlite'):
        driver_error = sqlite3.OperationalError('test database failure')
        driver_error.sqlite_errorcode = code
        error = OperationalError('test database failure')
        error.__cause__ = driver_error
        calls = []
        def view(request):
            calls.append(request.method)
            raise error
        request = RequestFactory().post('/')
        connection = SimpleNamespace(vendor=vendor, in_atomic_block=outer)
        with patch('apps.learning.request_serialization.connection', connection), patch(
            'apps.learning.request_serialization.transaction.atomic', side_effect=nullcontext
        ), patch('apps.learning.request_serialization.time.sleep'):
            if outer or vendor != 'sqlite' or code == sqlite3.SQLITE_ERROR:
                with self.assertRaises(OperationalError) as caught:
                    serialized_learning_post(view)(request)
                self.assertIs(caught.exception, error)
                self.assertEqual(len(calls), 1)
            else:
                self.assertEqual(serialized_learning_post(view)(request).status_code, 409)
                self.assertEqual(len(calls), 8)

    def test_busy_and_extended_locked_have_exactly_eight_attempts(self):
        for code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED_SHAREDCACHE):
            with self.subTest(code=code):
                self.exercise(code)

    def test_outer_atomic_and_unrelated_errors_are_not_retried(self):
        self.exercise(sqlite3.SQLITE_BUSY, outer=True)
        self.exercise(sqlite3.SQLITE_ERROR)
        self.exercise(sqlite3.SQLITE_BUSY, vendor='postgresql')

    def test_anonymous_posts_remain_login_redirects(self):
        for path in ('/learning/speech-practice/', '/learning/mistake-review/'):
            response = self.client.post(path)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/accounts/login/', response.url)
