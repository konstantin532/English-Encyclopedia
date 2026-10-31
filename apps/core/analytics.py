"""Аналитика урока в PostHog — только с сервера и только если задан POSTHOG_KEY.

Что уходит: три события урока (открыт, пройден, ошибка в упражнении) с кодом урока и номером
упражнения. Что не уходит никогда: имя, почта, текст ответа, IP-адрес, cookies, записи сессий.
В браузер скрипт PostHog не загружается, поэтому CSP не меняется и сторонних cookies нет.

ID ученика — псевдоним: HMAC от номера пользователя на SECRET_KEY. По нему нельзя узнать человека,
но можно посчитать уникальных учеников. Профили людей в PostHog не создаются.
Перед включением обновите политику конфиденциальности: PostHog — внешний сервис (152-ФЗ).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import threading
from typing import Any

from django.conf import settings

logger = logging.getLogger("apps.analytics")

# Новое событие — сначала сюда, с понятным смыслом; всё остальное отбрасывается.
EVENTS = {
    "lesson_opened": "Ученик открыл страницу урока",
    "lesson_completed": "Ученик впервые верно решил все упражнения урока",
    "exercise_mistake": "Проверенная ошибка в упражнении (свободный ответ ошибкой не считается)",
}
# Свойства без личных данных. Текст ответа, имя и почта сюда не попадают.
PROPERTIES = frozenset({"lesson", "level", "week", "exercise", "kind", "guest"})

_client = None
_client_lock = threading.Lock()


def enabled() -> bool:
    return bool(getattr(settings, "POSTHOG_KEY", ""))


def get_client():
    """Клиент создаётся при первом событии — уже после fork процессов gunicorn."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                from posthog import Posthog

                _client = Posthog(
                    settings.POSTHOG_KEY,
                    host=settings.POSTHOG_HOST,
                    disable_geoip=True,
                    timeout=5,
                    feature_flags_request_timeout_seconds=1,
                )
    return _client


def distinct_id(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        source = f"user:{user.pk}"
    else:
        session_key = getattr(getattr(request, "session", None), "session_key", None)
        if not session_key:
            return "guest"
        source = f"session:{session_key}"
    return hmac.new(settings.SECRET_KEY.encode(), source.encode(), hashlib.sha256).hexdigest()[:32]


def capture(request, event: str, **properties: Any) -> None:
    """Отправить событие урока. Сбой PostHog не ломает ответ ученику: ошибка только в журнал.

    Имена событий и свойств проверяются и без ключа: опечатку ловят обычные тесты.
    """
    if event not in EVENTS:
        raise ValueError(f"Неизвестное событие аналитики: {event}")
    unknown = set(properties) - PROPERTIES
    if unknown:
        raise ValueError(f"Свойства не из списка PROPERTIES: {sorted(unknown)}")
    if not enabled():
        return
    user = getattr(request, "user", None)
    payload = {**properties, "guest": not (user is not None and user.is_authenticated)}
    payload["$process_person_profile"] = False
    try:
        get_client().capture(event, distinct_id=distinct_id(request), properties=payload)
    except Exception:  # noqa: BLE001 — аналитика не важнее урока
        logger.warning("PostHog не принял событие %s", event, exc_info=True)


def lesson_properties(lesson) -> dict[str, Any]:
    week = getattr(lesson, "week", None)
    return {
        "lesson": lesson.slug,
        "level": lesson.level.code,
        "week": week.number if week is not None else None,
    }


def track_exercise(request, exercise, *, correct: bool, verified: bool) -> None:
    """После проверки ответа: проверенная ошибка или первое прохождение всего урока.

    Без ключа выходит сразу — ни одного лишнего запроса к базе.
    Непроверенный свободный ответ (verified=False) ошибкой не считается.
    """
    if not enabled() or not verified:
        return
    lesson = exercise.lesson
    if not correct:
        capture(request, "exercise_mistake", **lesson_properties(lesson), exercise=exercise.order, kind=exercise.kind)
    elif _first_lesson_completion(request.user, exercise):
        capture(request, "lesson_completed", **lesson_properties(lesson))


def _first_lesson_completion(user, exercise) -> bool:
    """Это верное решение — первое для упражнения, и после него решены все упражнения урока."""
    if not user.is_authenticated:
        return False
    from apps.learning.models import ExerciseAttempt

    solved = ExerciseAttempt.objects.filter(user=user, exercise__lesson_id=exercise.lesson_id, is_correct=True)
    if solved.filter(exercise=exercise).count() != 1:
        return False
    return solved.values("exercise").distinct().count() == exercise.lesson.exercises.count()
