"""Доступ к курсу: материалы открыты только после входа.

Без входа видно:
- главную, вход, регистрацию, страницу «Для учителей», служебные адреса;
- пробную неделю 1 уровня A1 (гостевой режим): страницу недели, её уроки,
  проверку её заданий и перенос гостевых ответов в новый аккаунт.

Всё остальное отправляет на вход и после входа возвращает обратно (?next=…).
Решение принимается по имени маршрута, а не по тексту адреса: переименование
адреса не откроет закрытую страницу случайно.
"""
import time

from django.conf import settings
from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.db import OperationalError, connection
from django.http import HttpResponse

# Чтение пользователя здесь происходит раньше защитных повторов внутри
# обработчиков (apps/learning/trainer_state.run_serialized). Поэтому временную
# блокировку SQLite («database table is locked/busy») повторяем так же: 8 раз
# с короткой растущей паузой. Другие ошибки не глотаем.
AUTH_READ_ATTEMPTS = 8

# Маршруты, открытые всем.
PUBLIC_ROUTES = frozenset({
    "core:home", "core:healthz", "core:robots", "core:sitemap",
    "core:metrics",  # закрыт своим токеном METRICS_TOKEN, без токена — 404
    "accounts:login", "accounts:signup", "accounts:logout",
    "teaching:for_teachers",
    "taxonomy:legend",  # объяснение цветных маркеров — справка, не материал курса
    "api:import_guest_progress", "api:guest_week_goal",
})
PUBLIC_NAMESPACES = frozenset({"admin"})  # у админки своя проверка входа

GUEST_LEVEL, GUEST_WEEK = "A1", 1


def _guest_lesson_slugs() -> frozenset[str]:
    from apps.lessons.models import Lesson
    return frozenset(Lesson.objects.filter(level__code=GUEST_LEVEL, week__number=GUEST_WEEK)
                     .values_list("slug", flat=True))


def _is_guest_week_route(name: str, kwargs: dict) -> bool:
    if name == "curriculum:week":
        return str(kwargs.get("slug", "")).lower() == GUEST_LEVEL.lower() and kwargs.get("number") == GUEST_WEEK
    if name == "lessons:detail":
        return kwargs.get("slug") in _guest_lesson_slugs()
    if name in ("api:check_exercise", "api:check_practice"):
        from apps.drills.models import Exercise, PracticeItem
        model = Exercise if name == "api:check_exercise" else PracticeItem
        return model.objects.filter(pk=kwargs.get("pk"), lesson__slug__in=_guest_lesson_slugs()).exists()
    return False


def is_public(request) -> bool:
    match = getattr(request, "resolver_match", None)
    if match is None:
        return False
    if match.namespace in PUBLIC_NAMESPACES or match.view_name in PUBLIC_ROUTES:
        return True
    return _is_guest_week_route(match.view_name, match.kwargs)


def _sqlite_lock(exc: OperationalError) -> bool:
    return connection.vendor == "sqlite" and any(w in str(exc).lower() for w in ("locked", "busy"))


def is_authenticated(request) -> bool | None:
    """True/False — ответ; None — база так и осталась занятой после всех повторов."""
    for attempt in range(AUTH_READ_ATTEMPTS):
        try:
            return bool(request.user.is_authenticated)
        except OperationalError as exc:
            # SimpleLazyObject не кэширует неудачу: следующая попытка читает заново.
            if not _sqlite_lock(exc) or connection.in_atomic_block:
                raise
            time.sleep(0.01 * (attempt + 1))
    return None


class CourseAccessMiddleware(LoginRequiredMiddleware):
    """Встроенный LoginRequiredMiddleware Django + открытые маршруты курса."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not settings.EE_COURSE_LOGIN_REQUIRED or is_public(request):
            return None
        authenticated = is_authenticated(request)
        if authenticated is None:
            response = HttpResponse("Сервер занят. Повторите через секунду.", status=503,
                                    content_type="text/plain; charset=utf-8")
            response["Retry-After"] = "1"
            return response
        if authenticated:
            return None
        return super().process_view(request, view_func, view_args, view_kwargs)
