"""Тренировка сгенерированных фраз, связанная с модулем «Память слов».

План дня строится по рейтингу слов ученика (memory.py), фразы — генератором
(phrase_engine), ответ проверяется одной общей проверкой (phrase_checker).
Состояние текущей тренировки хранится в сессии пользователя: отдельной таблицы нет.
Единицы пилота тренажёра (#130) сюда не попадают и не меняются.
"""
from __future__ import annotations

import math
import random
import uuid

from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone

from apps.lexicon.models import LexicalUnit, UnitType

from . import memory
from .models import UnitProgress
from .phrase_checker import check
from .phrase_engine import engine
from .phrase_engine.engine import STYPE_RU, make_phrase, tokenize
from .trainer_content import UNIT_UIDS as PILOT_UIDS

SESSION_KEY = "phrase_practice"
CONTENT_CLASSES = ("S", "D", "J", "A", "N")
SKIP_CLASSES = ("D1", "D7")


def content_version() -> str:
    agg = LexicalUnit.objects.aggregate(n=Count("id"), t=Max("updated_at"))
    return f"{agg['n']}:{agg['t'].isoformat() if agg['t'] else '-'}"


def is_content(unit) -> bool:
    return unit is not None and unit.cls.startswith(CONTENT_CLASSES) and unit.cls not in SKIP_CLASSES


def _progress_words(user):
    """Слова ученика, которые ведёт модуль памяти: есть UnitProgress, не пилот, не готовая фраза."""
    return (UnitProgress.objects.filter(user=user, unit__unit_type=UnitType.WORD)
            .exclude(unit__uid__in=PILOT_UIDS)
            .select_related("unit__internal_level", "unit__week"))


def learner_position(progress_list):
    """Позиция ученика: самая поздняя неделя среди единиц, с которыми он уже работал."""
    best = None
    for p in progress_list:
        u = p.unit
        pos = (u.internal_level.order - 1, u.week.number if u.week_id else 1)
        best = pos if best is None or pos > best else best
    return best


def _usable_lemmas(fams):
    out = set()
    for rows in fams.values():
        for r in rows:
            if r.note:
                out.add(r.note)
            for pool, _ in r.slots:
                for it in pool:
                    if it.unit is not None:
                        out.add(it.unit.lemma)
    return out


def word_states(user, now=None):
    """[(UnitProgress, рейтинг или None)] для слов ученика."""
    now = now or timezone.now()
    cfg = memory.config()
    return [(p, memory.rating(p, now, cfg)) for p in _progress_words(user)]


def plan_day(user, now=None, rng=None):
    """Очередь целевых слов на сегодня по правилам раздела 6 спецификации."""
    now = now or timezone.now()
    states = word_states(user, now)
    pos = learner_position([p for p, _ in states])
    if pos is None:
        return {"pos": None, "queue": []}
    ctx, fams, _ = engine.build_cached(content_version(), pos)
    usable = _usable_lemmas(fams)
    words = [(p, r) for p, r in states if p.unit.lemma in usable and is_content(ctx.U.get(p.unit.lemma))]
    if not words:
        return {"pos": pos, "queue": []}
    level = max(states, key=lambda s: (s[0].unit.internal_level.order, s[0].unit.week.number if s[0].unit.week_id else 0))[0].unit.internal_level.code
    cfg = memory.config(level)
    sc = cfg["session"]
    rng = rng or random.Random(f"{user.pk}:{timezone.localdate(now)}")
    due = sum(1 for _, r in words if r is None or r < sc["due_below"])
    n = max(sc["min_phrases"], min(sc["max_phrases"], math.ceil(due / sc["words_per_phrase"])))
    n = min(n, len(words) * sc["per_word_max"])
    eff = {p.unit.lemma: (30.0 if r is None else r) for p, r in words}
    low = [w for w in eff if eff[w] < 80]
    mid = [w for w in eff if 80 <= eff[w] < 95]
    high = [w for w in eff if eff[w] >= 95]
    per = {}

    def take(pool, k):
        got = []
        pool = list(pool)
        while len(got) < k and pool:
            w = rng.choices(pool, [memory.chance(eff[x], cfg) for x in pool])[0]
            got.append(w)
            per[w] = per.get(w, 0) + 1
            if per[w] >= sc["per_word_max"]:
                pool.remove(w)
        return got
    n_low = round(n * sc["share_low"])
    n_mid = round(n * sc["share_mid"])
    urgent = []
    for p, r in words:
        ev = p.memory_evidence or {}
        if r is not None and r < sc["urgent_below"] and p.memory_reviewed_at and \
                (now - p.memory_reviewed_at).days > sc["urgent_days"]:
            urgent.append(p.unit.lemma)
    plan = urgent[:n_low]
    for w in plan:
        per[w] = per.get(w, 0) + 1
    plan += take([w for w in low if per.get(w, 0) < sc["per_word_max"]], n_low - len(plan))
    plan += take([w for w in mid if per.get(w, 0) < sc["per_word_max"]], n_mid)
    plan += take([w for w in high if per.get(w, 0) < sc["per_word_max"]], n - len(plan))
    plan += take([w for w in eff if per.get(w, 0) < sc["per_word_max"]], n - len(plan))
    # одно слово — не чаще раза в 3 фразы (если есть из чего выбирать)
    order, pending = [], plan[:]
    while pending:
        pick = next((w for w in pending if w not in order[-2:]), pending[0])
        pending.remove(pick)
        order.append(pick)
    return {"pos": pos, "queue": order}


# ─────────── текущая тренировка в сессии ───────────
def _state(request):
    return request.session.get(SESSION_KEY) or {}


def _save(request, state):
    request.session[SESSION_KEY] = state
    request.session.modified = True


def current(request, now=None):
    """Текущее задание (создаёт план дня и следующую фразу при необходимости)."""
    now = now or timezone.now()
    user = request.user
    today = timezone.localdate(now).isoformat()
    st = _state(request)
    if st.get("day") != today or st.get("user") != user.pk:
        plan = plan_day(user, now)
        st = {"day": today, "user": user.pk, "pos": plan["pos"], "queue": plan["queue"], "i": 0,
              "item": None, "correct": 0, "errors": 0}
    if st.get("item") is None or st["item"].get("answered") and st["item"].get("advance"):
        st["item"] = _next_item(user, st, now)
    _save(request, st)
    return st


def _next_item(user, st, now):
    if st["pos"] is None:
        return None
    ctx, fams, index = engine.build_cached(content_version(), tuple(st["pos"]))
    progress = {p.unit.lemma: p for p in _progress_words(user)}
    cfg = memory.config()
    familiar = frozenset(l for l, p in progress.items()
                         if (r := memory.rating(p, now, cfg)) is not None and r >= cfg["session"]["familiar_from"])
    while st["i"] < len(st["queue"]):
        target = st["queue"][st["i"]]
        st["i"] += 1
        rng = random.Random(f"{user.pk}:{st['day']}:{st['i']}:{target}")
        phrase = make_phrase(ctx, fams, target, rng, familiar, index)
        if phrase is None:
            continue
        prog = progress.get(target)
        r = memory.rating(prog, now, cfg) if prog else None
        mode = memory.pick_mode(prog, r) if prog else "full"
        fams_seen = (prog.memory_evidence or {}).get("families", []) if prog else []
        if mode == "independent" and fams_seen and phrase.family not in fams_seen:
            mode = "transfer"
        return _item_payload(ctx, phrase, mode, rng, st["i"], len(st["queue"]))
    return None


def _item_payload(ctx, phrase, mode, rng, number, total):
    words = tokenize(phrase.text)
    bank = list(words)
    if bank:  # заглавная буква первого слова — только из-за начала фразы (кроме I, TV, Monday …)
        first_lemma = phrase.lemmas[0] if phrase.lemmas else None
        if not (first_lemma and first_lemma[:1].isupper()):
            bank[0] = bank[0].lower()
    shuffled = bank[:]
    for _ in range(10):
        rng.shuffle(shuffled)
        if shuffled != bank or len(bank) < 2:
            break
    glosses, seen = [], set()
    for lem in phrase.lemmas:
        u = ctx.U.get(lem) if lem else None
        if is_content(u) and lem not in seen:
            seen.add(lem)
            glosses.append({"en": lem, "ru": u.translation, "target": lem == phrase.target})
    return {
        "id": uuid.uuid4().hex, "number": number, "total": total,
        "family": phrase.family, "family_name_ru": phrase.family_name_ru,
        "stype": phrase.stype, "stype_ru": STYPE_RU[phrase.stype],
        "target": phrase.target, "lemmas": phrase.lemmas, "accepted": phrase.accepted,
        "mode": mode, "bank": shuffled if mode in ("full", "partial") else [],
        "first_word": words[0] if mode == "full" and words else "",
        "glosses": glosses, "answered": False, "advance": False, "result": None,
    }


def answer(request, item_id: str, text: str, now=None):
    """Проверка ответа и запись памяти. Повтор того же запроса ничего не меняет."""
    now = now or timezone.now()
    st = _state(request)
    item = st.get("item")
    if not item or item["id"] != item_id:
        return None
    if item["answered"]:
        return item["result"]
    ctx, fams, index = engine.build_cached(content_version(), tuple(st["pos"]))
    res = check(text, item["accepted"], item["lemmas"], index, ctx.U)
    changes = _apply_memory(request.user, ctx, item, res, now)
    item["answered"] = True
    item["result"] = {
        "status": res.status, "kind": res.kind, "correct": res.correct, "got": res.got,
        "expected": res.expected, "confidence": res.confidence, "explanation_ru": res.explanation_ru,
        "sample": res.sample, "lemma": res.lemma, "answer": text[:300], "changes": changes,
    }
    st["correct" if res.correct else "errors"] += 1
    _save(request, st)
    return item["result"]


def advance(request):
    st = _state(request)
    if st.get("item") and st["item"].get("answered"):
        st["item"]["advance"] = True
        _save(request, st)


@transaction.atomic
def _apply_memory(user, ctx, item, res, now):
    content = []
    for lem in item["lemmas"]:
        u = ctx.U.get(lem) if lem else None
        if is_content(u) and u.uid not in PILOT_UIDS and lem not in content:
            content.append(lem)
    if res.status == "unsure":
        return []
    if res.correct:
        targets = [(lem, dict(correct=True, mode=item["mode"], family=f"phrase:{item['family']}")) for lem in content]
    elif res.kind == "empty" and item["target"] in content:
        targets = [(item["target"], dict(correct=False, error="dontknow", mode=item["mode"]))]
    elif res.lemma and res.memory_error and res.confidence != "low" and res.lemma in content:
        targets = [(res.lemma, dict(correct=False, error=res.memory_error, mode=item["mode"]))]
    else:
        return []  # ошибка в построении фразы (порядок, лишнее слово) — не штраф отдельному слову
    uids = {ctx.U[lem].uid: lem for lem, _ in targets}
    units = {u.uid: u for u in LexicalUnit.objects.filter(uid__in=uids)}
    changes = []
    for lem, kw in targets:
        unit = units.get(ctx.U[lem].uid)
        if unit is None:
            continue
        prog, _ = UnitProgress.objects.select_for_update().get_or_create(user=user, unit=unit)
        log = memory.apply(prog, now=now, **kw)
        prog.save(update_fields=["memory_stability", "memory_reviewed_at", "memory_evidence", "updated_at"])
        changes.append({"lemma": lem, "before": log["display_before"], "after": log["display_after"]})
    return changes


def summary(user, now=None):
    """Сколько слов ученика в каждой стадии — для страницы."""
    now = now or timezone.now()
    cfg = memory.config()
    counts = {}
    for p in _progress_words(user):
        name = memory.stage_name(memory.display_rating(p, now, cfg), cfg)
        counts[name] = counts.get(name, 0) + 1
    order = ["Новое"] + [s[2] for s in cfg["stages"]]
    return [(name, counts[name]) for name in order if name in counts]
