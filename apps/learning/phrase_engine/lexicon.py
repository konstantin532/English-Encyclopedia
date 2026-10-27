"""Словарь для генератора: единицы курса из базы + черновая разметка признаков.

Связь с разметкой — по лемме: в курсе лемма однозначна (повторы запрещены
audit_duplicate_words). Единица без разметки остаётся в словаре, но в шаблоны
не попадает, пока редактор не добавит её признаки.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from django.conf import settings

MARKUP_FILES = ("nouns.txt", "verbs.txt", "adjectives.txt", "functionals.txt")


def markup_dir() -> Path:
    return Path(settings.CONTENT_DIR) / "phrase_engine"


@dataclass
class Unit:
    uid: str
    lemma: str
    cls: str
    level: str
    level_order: int
    week: int
    forms: list
    ipa: str
    translation: str
    tags: set = field(default_factory=set)
    count: str = ""
    flags: dict = field(default_factory=dict)
    frames: list = field(default_factory=list)
    prog: bool = True
    past: str = ""
    applies: set = field(default_factory=set)
    position: str = ""
    gradable: bool = False
    role: str = ""
    review: list = field(default_factory=list)
    marked: bool = False

    @property
    def pos(self):
        """Позиция в курсе: (порядок уровня с нуля, неделя). Новые уровни — по Level.order."""
        return (self.level_order - 1, self.week)

    @property
    def pos_letter(self):
        return self.cls[0]


def _lines(name):
    path = markup_dir() / name
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        yield [c.strip() for c in raw.split("|")]


def _flags(text):
    flags, review = {}, []
    m = re.search(r"review=(.*)$", text)
    if m:
        review.append(m.group(1).strip())
        text = text[: m.start()]
    for tok in text.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            flags[k] = v
        else:
            flags[tok] = True
    return flags, review


def apply_markup(units: dict[str, Unit]) -> list[str]:
    """Присоединяет признаки к единицам. Возвращает список несоответствий."""
    problems = []

    def get(lemma, src):
        u = units.get(lemma)
        if u is None:
            problems.append(f"{src}: «{lemma}» есть в разметке, но нет в словаре")
        return u

    for cols in _lines("nouns.txt"):
        lemma, tags, count, rest = (cols + [""] * 4)[:4]
        if (u := get(lemma, "nouns.txt")):
            u.tags, u.count = set(tags.split()), count
            u.flags, u.review = _flags(rest)
            u.marked = True
    for cols in _lines("verbs.txt"):
        lemma, frames, prog, past = cols[:4]
        if (u := get(lemma, "verbs.txt")):
            u.frames = [f.strip() for f in frames.split(";") if f.strip()]
            u.prog, u.past, u.marked = prog == "yes", past, True
            if len(cols) > 4 and cols[4].startswith("review"):
                u.review.append(cols[4])
    for cols in _lines("adjectives.txt"):
        lemma, applies, position, gradable = cols[:4]
        if (u := get(lemma, "adjectives.txt")):
            u.applies, u.position = set(applies.split()), position
            u.gradable, u.marked = gradable == "yes", True
    for cols in _lines("functionals.txt"):
        lemma, role = cols[:2]
        if (u := get(lemma, "functionals.txt")):
            u.role, u.marked = role, True
    return problems


def units_from_db() -> dict[str, Unit]:
    from apps.lexicon.models import LexicalUnit, UnitType

    out = {}
    qs = (LexicalUnit.objects.filter(unit_type=UnitType.WORD)
          .select_related("semantic_class__category", "internal_level", "week"))
    for lu in qs:
        out[lu.lemma] = Unit(
            uid=lu.uid, lemma=lu.lemma, cls=lu.markup_code, level=lu.internal_level.code,
            level_order=lu.internal_level.order, week=lu.week.number if lu.week_id else 1,
            forms=list(lu.forms or []), ipa=lu.ipa_us, translation=lu.translation_ru,
        )
    return out


@lru_cache(maxsize=4)
def _cached(version: str):
    units = units_from_db()
    problems = apply_markup(units)
    return units, tuple(problems)


def load(version: str = "") -> tuple[dict[str, Unit], tuple[str, ...]]:
    """Словарь с признаками. version — ключ кэша (например, версия контента)."""
    return _cached(version)


def clear_cache():
    _cached.cache_clear()
