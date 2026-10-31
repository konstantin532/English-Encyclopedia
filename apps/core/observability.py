"""Наблюдаемость: журналы в JSON, сквозной ID запроса, счётчики для /metrics/ и Sentry.

Модуль не импортирует модели: его подключают настройки (LOGGING, init_sentry) до запуска Django.

- Каждый запрос получает ID (заголовок X-Request-ID): он есть в ответе, в каждой строке журнала
  и в событии Sentry, поэтому жалобу «упало в 14:02» можно найти по одному значению.
- /metrics/ отдаёт счётчики в формате Prometheus только с токеном METRICS_TOKEN; без токена — 404.
  Счётчики живут в памяти процесса: при нескольких процессах gunicorn каждый считает своё.
- Sentry включается только при SENTRY_DSN. Личные данные не уходят: без cookies, заголовков,
  тела запроса, строки запроса и локальных переменных.
"""

from __future__ import annotations

import hmac
import json
import logging
import re
import threading
import time
import uuid
from collections import Counter
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

REQUEST_ID_HEADER = "X-Request-ID"
# Чужой ID принимаем, только если он безопасен для журнала: без пробелов и переводов строк.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_KNOWN_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})
_QUIET_PREFIXES = ("/static/", "/media/", "/healthz/", "/metrics/")

request_logger = logging.getLogger("apps.request")

# Поля LogRecord, которые есть всегда; всё остальное пришло через extra={...}.
_STANDARD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime", "request_id"}


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Одна строка JSON на событие: удобно искать и считать в любом сборщике журналов."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id_var.get()),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class Metrics:
    """Счётчики запросов в формате Prometheus. Метки ограничены: метод, класс статуса, имя маршрута."""

    BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.started = time.time()
        self.requests: Counter[tuple[str, str, str]] = Counter()
        self.duration_buckets = [0] * len(self.BUCKETS)
        self.duration_sum = 0.0
        self.duration_count = 0

    def observe(self, method: str, status: int, view: str, seconds: float) -> None:
        method = method if method in _KNOWN_METHODS else "OTHER"
        with self._lock:
            self.requests[(method, f"{status // 100}xx", view)] += 1
            self.duration_sum += seconds
            self.duration_count += 1
            for index, bound in enumerate(self.BUCKETS):
                if seconds <= bound:
                    self.duration_buckets[index] += 1

    def render(self, release: str = "") -> str:
        with self._lock:
            lines = [
                "# HELP ee_build_info Версия сайта.",
                "# TYPE ee_build_info gauge",
                f'ee_build_info{{release="{_label(release or "unknown")}"}} 1',
                "# HELP ee_process_start_time_seconds Время запуска процесса.",
                "# TYPE ee_process_start_time_seconds gauge",
                f"ee_process_start_time_seconds {self.started:.0f}",
                "# HELP ee_http_requests_total Запросы по методу, классу статуса и маршруту.",
                "# TYPE ee_http_requests_total counter",
            ]
            for (method, status, view), count in sorted(self.requests.items()):
                lines.append(
                    f'ee_http_requests_total{{method="{method}",status="{status}",view="{_label(view)}"}} {count}'
                )
            lines += [
                "# HELP ee_http_request_duration_seconds Время ответа.",
                "# TYPE ee_http_request_duration_seconds histogram",
            ]
            for bound, count in zip(self.BUCKETS, self.duration_buckets, strict=True):
                lines.append(f'ee_http_request_duration_seconds_bucket{{le="{bound}"}} {count}')
            lines += [
                f'ee_http_request_duration_seconds_bucket{{le="+Inf"}} {self.duration_count}',
                f"ee_http_request_duration_seconds_sum {self.duration_sum:.6f}",
                f"ee_http_request_duration_seconds_count {self.duration_count}",
            ]
        return "\n".join(lines) + "\n"


def _label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


METRICS = Metrics()


def _incoming_request_id(request) -> str:
    supplied = request.headers.get(REQUEST_ID_HEADER, "")
    return supplied if _SAFE_REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex


class RequestIDMiddleware:
    """Первый в MIDDLEWARE: ID и замер времени охватывают всю обработку запроса."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = _incoming_request_id(request)
        request.request_id = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            _sentry_tag("request_id", request_id)
            response = self.get_response(request)
            elapsed = time.perf_counter() - started
            match = getattr(request, "resolver_match", None)
            view = match.view_name if match and match.view_name else "unmatched"
            METRICS.observe(request.method, response.status_code, view, elapsed)
            response[REQUEST_ID_HEADER] = request_id
            if not request.path.startswith(_QUIET_PREFIXES):
                # Только путь, без строки запроса: в ней бывают адреса почты и ответы учеников.
                request_logger.info(
                    "%s %s %s",
                    request.method,
                    request.path,
                    response.status_code,
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.path,
                        "status": response.status_code,
                        "view": view,
                        "duration_ms": round(elapsed * 1000, 1),
                    },
                )
            return response
        finally:
            request_id_var.reset(token)


def metrics_view(request):
    from django.conf import settings
    from django.http import Http404, HttpResponse

    expected = getattr(settings, "METRICS_TOKEN", "")
    if not expected:
        raise Http404
    supplied = request.headers.get("Authorization", "")
    if not hmac.compare_digest(supplied.encode(), f"Bearer {expected}".encode()):
        response = HttpResponse("Нужен токен METRICS_TOKEN.", status=401, content_type="text/plain; charset=utf-8")
        response["WWW-Authenticate"] = "Bearer"
        return response
    response = HttpResponse(
        METRICS.render(getattr(settings, "SENTRY_RELEASE", "")),
        content_type="text/plain; version=0.0.4; charset=utf-8",
    )
    response["Cache-Control"] = "no-store"
    return response


# --- Sentry -----------------------------------------------------------------

_SCRUBBED_REQUEST_KEYS = ("cookies", "data", "headers", "query_string", "env")


def scrub_event(event, hint=None):
    """Убирает из события всё, что может содержать личные данные ученика."""
    request = event.get("request")
    if isinstance(request, dict):
        for key in _SCRUBBED_REQUEST_KEYS:
            request.pop(key, None)
        if isinstance(request.get("url"), str):
            request["url"] = request["url"].split("?", 1)[0]
    event.pop("user", None)
    return event


def init_sentry(dsn: str, *, environment: str, release: str, traces_sample_rate: float) -> bool:
    if not dsn:
        return False
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=dsn,
        integrations=[DjangoIntegration()],
        environment=environment,
        release=release or None,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        before_send=scrub_event,
        before_send_transaction=scrub_event,
    )
    return True


def _sentry_tag(key: str, value: str) -> None:
    try:
        import sentry_sdk
    except ImportError:  # pragma: no cover — sentry-sdk в основных зависимостях
        return
    sentry_sdk.set_tag(key, value)
