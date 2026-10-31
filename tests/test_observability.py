"""Наблюдаемость: ID запроса, журнал JSON, закрытые метрики и Sentry без личных данных."""

import json
import logging

from django.test import SimpleTestCase, TestCase, override_settings

from apps.core import observability
from apps.core.observability import JsonFormatter, RequestIDFilter, init_sentry, request_id_var, scrub_event


class RequestIdTests(TestCase):
    def test_every_response_gets_a_request_id(self):
        response = self.client.get("/healthz/")
        self.assertRegex(response["X-Request-ID"], r"^[0-9a-f]{32}$")
        self.assertNotEqual(response["X-Request-ID"], self.client.get("/healthz/")["X-Request-ID"])

    def test_safe_incoming_id_is_kept_and_unsafe_is_replaced(self):
        kept = self.client.get("/healthz/", headers={"X-Request-ID": "caddy-0123456789"})
        self.assertEqual(kept["X-Request-ID"], "caddy-0123456789")
        replaced = self.client.get("/healthz/", headers={"X-Request-ID": "bad id\nforged log line"})
        self.assertRegex(replaced["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_access_log_has_request_id_and_no_query_string(self):
        with self.assertLogs("apps.request", level="INFO") as logs:
            response = self.client.get("/", {"email": "learner@example.test"})
        record = logs.records[-1]
        self.assertEqual(record.path, "/")
        self.assertEqual(record.status, response.status_code)
        self.assertEqual(record.view, "core:home")
        line = JsonFormatter().format(record)
        self.assertNotIn("learner@example.test", line)
        self.assertEqual(json.loads(line)["request_id"], response["X-Request-ID"])

    def test_request_id_does_not_leak_between_requests(self):
        self.client.get("/healthz/")
        self.assertEqual(request_id_var.get(), "-")


class JsonFormatterTests(SimpleTestCase):
    def test_one_json_object_per_line_with_extra_fields(self):
        record = logging.LogRecord("apps.x", logging.WARNING, __file__, 1, "Ученик %s", ("A",), None)
        record.lesson = "a1-hello"
        RequestIDFilter().filter(record)
        payload = json.loads(JsonFormatter().format(record))
        self.assertEqual(payload["message"], "Ученик A")
        self.assertEqual(payload["level"], "WARNING")
        self.assertEqual(payload["lesson"], "a1-hello")
        self.assertEqual(payload["request_id"], "-")

    def test_exception_is_included(self):
        try:
            raise ValueError("сломалось")
        except ValueError:
            import sys

            record = logging.LogRecord("apps.x", logging.ERROR, __file__, 1, "ошибка", (), sys.exc_info())
        self.assertIn("ValueError: сломалось", json.loads(JsonFormatter().format(record))["exc_info"])


@override_settings(EE_COURSE_LOGIN_REQUIRED=True)
class MetricsEndpointTests(TestCase):
    @override_settings(METRICS_TOKEN="")
    def test_hidden_without_configured_token(self):
        self.assertEqual(self.client.get("/metrics/").status_code, 404)

    @override_settings(METRICS_TOKEN="s3cret-token")
    def test_wrong_or_missing_token_is_rejected(self):
        self.assertEqual(self.client.get("/metrics/").status_code, 401)
        wrong = self.client.get("/metrics/", headers={"Authorization": "Bearer nope"})
        self.assertEqual(wrong.status_code, 401)
        self.assertNotIn("ee_http_requests_total", wrong.content.decode())

    @override_settings(METRICS_TOKEN="s3cret-token")
    def test_prometheus_text_with_token_and_without_login(self):
        self.client.get("/healthz/")
        response = self.client.get("/metrics/", headers={"Authorization": "Bearer s3cret-token"})
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('ee_http_requests_total{method="GET",status="2xx",view="core:healthz"}', body)
        self.assertIn('ee_http_request_duration_seconds_bucket{le="+Inf"}', body)
        self.assertEqual(response["Cache-Control"], "no-store")


class MetricsCardinalityTests(SimpleTestCase):
    def test_labels_stay_bounded(self):
        metrics = observability.Metrics()
        metrics.observe("BREW", 418, "unmatched", 0.01)
        metrics.observe("GET", 503, 'evil"view', 9.0)
        body = metrics.render()
        self.assertIn('method="OTHER",status="4xx"', body)
        self.assertIn('view="evil\\"view"', body)
        self.assertIn("ee_http_request_duration_seconds_count 2", body)


class SentryPrivacyTests(SimpleTestCase):
    def test_disabled_without_dsn(self):
        self.assertFalse(init_sentry("", environment="test", release="", traces_sample_rate=0.0))

    def test_event_loses_personal_data(self):
        event = {
            "request": {
                "url": "https://example.test/learning/?email=a@b.test",
                "query_string": "email=a@b.test",
                "cookies": {"sessionid": "x"},
                "headers": {"Cookie": "sessionid=x"},
                "data": {"answer": "my name is Anna"},
                "method": "POST",
            },
            "user": {"email": "a@b.test", "ip_address": "1.2.3.4"},
        }
        cleaned = scrub_event(event)
        self.assertEqual(cleaned["request"], {"url": "https://example.test/learning/", "method": "POST"})
        self.assertNotIn("user", cleaned)
