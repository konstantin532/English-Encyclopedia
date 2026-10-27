"""Модуль «Память слов»: рейтинг слова как вероятность вспомнить.

Хранит всё в UnitProgress (memory_stability, memory_reviewed_at, memory_evidence) —
отдельного журнала прогресса нет. Расписание прежнего повторения (stage,
next_review_at) модуль не меняет. Числа — в content/phrase_engine/memory.yaml.
Включается настройкой EE_PHRASE_MEMORY_ENABLED; выключенный модуль ничего не пишет.
"""
from __future__ import annotations

import copy
import math
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import yaml
from django.conf import settings
from django.utils import timezone

MODES = ("full", "puzzle", "partial", "independent", "transfer")
ERRORS = ("typo", "form", "wrong", "dontknow")


def enabled() -> bool:
    return bool(getattr(settings, "EE_PHRASE_MEMORY_ENABLED", False))


@lru_cache(maxsize=1)
def _raw_config() -> dict:
    path = Path(settings.CONTENT_DIR) / "phrase_engine" / "memory.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def config(level: str | None = None) -> dict:
    """Общие настройки, поверх них — переопределения уровня (если заданы)."""
    base = copy.deepcopy(_raw_config())
    over = (base.get("levels") or {}).get(level or "", {}) or {}
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key].update(value)
        else:
            base[key] = value
    return base


# ─────────── расчёт рейтинга (без записи) ───────────
def _days(a: datetime, b: datetime) -> float:
    return max(0.0, (b - a).total_seconds() / 86400)


def recall(stability: float, reviewed_at: datetime, now: datetime) -> float:
    """Вероятность вспомнить (0…1)."""
    return 0.9 ** (_days(reviewed_at, now) / max(stability, 1e-6))


def rating(progress, now=None, cfg=None) -> float | None:
    """Рейтинг 0–100 или None, если слово ещё не в модуле памяти."""
    if progress.memory_stability is None or progress.memory_reviewed_at is None:
        return None
    cfg = cfg or config()
    now = now or timezone.now()
    r = 100 * recall(progress.memory_stability, progress.memory_reviewed_at, now)
    ev = progress.memory_evidence or {}
    m = cfg["mastery"]
    if r >= m["threshold"] and (len(ev.get("days", [])) < m["days"] or len(ev.get("families", [])) < m["families"]):
        r = min(r, m["threshold"] - 1)  # до 80% — только за 3 дня и 2 семейства
    return r


def display_rating(progress, now=None, cfg=None) -> float | None:
    """Рейтинг для подписи ученику: не выше, чем позволяет число дней с верными ответами."""
    cfg = cfg or config()
    r = rating(progress, now, cfg)
    if r is None:
        return None
    days = len((progress.memory_evidence or {}).get("days", []))
    caps = {int(k): v for k, v in (cfg.get("display_cap_by_days") or {}).items()}
    if days in caps:
        r = min(r, caps[days])
    elif days == 0 and caps:
        r = min(r, min(caps.values()))
    return r


def stage(r: float, cfg=None) -> int:
    cfg = cfg or config()
    s = 0
    for i, (low, _chance, _name) in enumerate(cfg["stages"]):
        if r >= low:
            s = i
    return s


def stage_name(r: float | None, cfg=None) -> str:
    if r is None:
        return "Новое"
    cfg = cfg or config()
    return cfg["stages"][stage(r, cfg)][2]


def chance(r: float | None, cfg=None) -> float:
    """Шанс (вес) слова попасть во фразу, 0…1. Новое слово — как «Слабое»."""
    cfg = cfg or config()
    if r is None:
        r = 30.0
    return cfg["stages"][stage(r, cfg)][1] / 100


def strength_step(stability: float | None, cfg=None) -> int:
    """Ступень прочности 0–8 — подпись к прочности в днях."""
    if stability is None:
        return 0
    cfg = cfg or config()
    step = 0
    for i, days in enumerate(cfg["strength_steps_days"]):
        if stability >= days:
            step = i
    return step


# ─────────── обновление после ответа ───────────
def _local_day(now: datetime) -> str:
    return timezone.localdate(now).isoformat()


def start(progress, now=None, cfg=None) -> None:
    """Слово попадает в модуль памяти (первое знакомство или первый ответ)."""
    if progress.memory_stability is not None:
        return
    cfg = cfg or config()
    progress.memory_stability = float(cfg["start_stability_days"])
    progress.memory_reviewed_at = now or timezone.now()
    progress.memory_evidence = dict(progress.memory_evidence or {})


def apply(progress, *, correct: bool, mode: str = "independent", error: str = "wrong",
          family: str = "", now=None, cfg=None) -> dict:
    """Применяет ответ к памяти слова. Возвращает краткий журнал изменения.

    Верный ответ умножает прочность (не чаще раза в день), ошибка делит её.
    Повтор одного и того же ответа защищает вызывающий код (идемпотентность запроса).
    """
    if mode not in MODES:
        raise ValueError(f"Неизвестный режим ответа: {mode}")
    if not correct and error not in ERRORS:
        raise ValueError(f"Неизвестный тип ошибки: {error}")
    cfg = cfg or config()
    now = now or timezone.now()
    start(progress, now, cfg)
    ev = dict(progress.memory_evidence or {})
    before = rating(progress, now, cfg)
    display_before = display_rating(progress, now, cfg)
    s_before = progress.memory_stability
    R = recall(progress.memory_stability, progress.memory_reviewed_at, now)
    today = _local_day(now)
    if correct:
        if ev.get("grown_on") != today:
            progress.memory_stability *= 1 + cfg["growth_k"][mode] * math.sqrt(max(0.0, 1 - R))
            ev["grown_on"] = today
        days = list(ev.get("days", []))
        if today not in days:
            days = (days + [today])[-30:]
        ev["days"] = days
        if family:
            fams = list(ev.get("families", []))
            if family not in fams:
                fams = (fams + [family])[-20:]
            ev["families"] = fams
        ev["streak"] = 0
    else:
        progress.memory_stability = max(cfg["min_stability_days"],
                                        progress.memory_stability * cfg["error_multiplier"][error])
        ev["streak"] = int(ev.get("streak", 0)) + 1
        if ev["streak"] >= cfg["hint_after_errors"]:
            ev["hint_left"] = cfg["hint_phrases"]
    if ev.get("hint_left") and mode in ("full", "puzzle"):
        ev["hint_left"] = max(0, int(ev["hint_left"]) - 1)
    progress.memory_reviewed_at = now
    progress.memory_evidence = ev
    after = rating(progress, now, cfg)
    return {"before": before, "after": after,
            "display_before": display_before, "display_after": display_rating(progress, now, cfg),
            "stability_before": s_before, "stability_after": progress.memory_stability,
            "rules_version": cfg["version"]}


def needs_hint(progress) -> bool:
    return bool((progress.memory_evidence or {}).get("hint_left"))


def pick_mode(progress, r: float | None) -> str:
    """Какую помощь показать: ниже 40% или после серии ошибок — полная подсказка."""
    if needs_hint(progress) or r is None or r < 40:
        return "full"
    if r < 60:
        return "partial"
    return "independent"


# ─────────── способ ввода: пазл или набор ───────────
def puzzle_percent(correct_total: int, cfg=None) -> int:
    """Доля пазлов (0–100) для ученика с таким числом верных фраз за всё время."""
    cfg = cfg or config()
    share = 100
    for start, percent in cfg["input"]["puzzle_steps"]:
        if correct_total >= start:
            share = percent
    return share


def puzzle_step(correct_total: int, cfg=None) -> int:
    """Номер ступени перехода: 0 — только пазлы, последняя — постоянная доля пазлов."""
    cfg = cfg or config()
    return sum(1 for start, _ in cfg["input"]["puzzle_steps"][1:] if correct_total >= start)
