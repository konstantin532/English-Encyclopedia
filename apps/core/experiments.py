"""Эксперименты: флаги PostHog с безопасным значением по умолчанию.

    from apps.core.experiments import variant
    if variant(request, "lesson-hint-style") == "example-first":
        ...

Пока PostHog не настроен (нет POSTHOG_KEY) или не ответил за секунду, каждый ученик получает
значение по умолчанию — сайт ведёт себя так же, как без эксперимента.
Новый флаг — сначала в FLAGS: имя, значение по умолчанию и допустимые варианты.
Реальный эксперимент запускает автор: флаг создаётся в PostHog с теми же вариантами.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from apps.core import analytics

logger = logging.getLogger("apps.experiments")


@dataclass(frozen=True)
class Flag:
    default: str
    variants: frozenset[str]
    purpose: str


FLAGS = {
    # Пример, не запущен: подсказка к упражнению — сначала правило или сначала пример.
    "lesson-hint-style": Flag(
        default="rule-first",
        variants=frozenset({"rule-first", "example-first"}),
        purpose="Помогает ли пример перед правилом реже ошибаться в упражнениях урока",
    ),
}


def variant(request, key: str) -> str:
    flag = FLAGS[key]
    if not analytics.enabled():
        return flag.default
    try:
        value = analytics.get_client().get_feature_flag(key, analytics.distinct_id(request), disable_geoip=True)
    except Exception:  # noqa: BLE001 — эксперимент не должен ломать урок
        logger.warning("PostHog не вернул флаг %s", key, exc_info=True)
        return flag.default
    return value if isinstance(value, str) and value in flag.variants else flag.default
