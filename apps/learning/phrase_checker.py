"""Проверка ответа на сгенерированную фразу — одна для всех семейств.

Сравнивает ответ ученика с допустимыми написаниями после нормализации
(регистр, пунктуация, сокращения). Если ответ не совпал, находит ПЕРВОЕ
расхождение (вторичные ошибки не порождают цепочку сообщений), определяет
его тип и слово, к которому оно относится. Неуверенный диагноз не штрафует слово.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

CONTRACTIONS = {
    "i'm": "i am", "you're": "you are", "we're": "we are", "they're": "they are",
    "he's": "he is", "she's": "she is", "it's": "it is", "that's": "that is", "there's": "there is",
    "what's": "what is", "where's": "where is", "who's": "who is",
    "isn't": "is not", "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "can't": "cannot", "won't": "will not", "mustn't": "must not",
    "i'll": "i will", "you'll": "you will", "he'll": "he will", "she'll": "she will",
    "we'll": "we will", "they'll": "they will", "it'll": "it will",
}


def normalize(text: str) -> list[str]:
    text = (text or "").replace("’", "'").replace("‘", "'").lower()
    text = re.sub(r"\bcan not\b", "cannot", text)
    words = re.findall(r"[a-z]+(?:'[a-z]+)?", text)
    out = []
    for w in words:
        out += CONTRACTIONS.get(w, w).split()
    return out


def _show(word: str) -> str:
    return "I" if word == "i" else word


def _edit1(a: str, b: str) -> bool:
    """Одна буква заменена, пропущена, добавлена или переставлены соседние."""
    if a == b or abs(len(a) - len(b)) > 1 or min(len(a), len(b)) < 3:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1
                                   and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    s, t = (a, b) if len(a) < len(b) else (b, a)
    return any(t[:i] + t[i + 1:] == s for i in range(len(t)))


@dataclass
class Result:
    status: str                    # correct | correct_alt | error | unsure
    kind: str = ""                 # order | form | typo | wrong | missing | extra | empty
    memory_error: str = ""         # тип ошибки для модуля памяти: typo | form | wrong | dontknow
    lemma: str | None = None       # к какому слову относится ошибка (None — к построению фразы)
    got: str = ""
    expected: str = ""
    confidence: str = "high"       # high | medium | low
    explanation_ru: str = ""
    sample: str = ""
    notes: list = field(default_factory=list)

    @property
    def correct(self) -> bool:
        return self.status in ("correct", "correct_alt")


FUNCTION_CLASSES = ("T", "P", "X", "C", "D1", "D7")


def _is_function(lemma, units):
    u = units.get(lemma) if lemma else None
    return u is not None and (u.cls.startswith(FUNCTION_CLASSES[:4]) or u.cls in FUNCTION_CLASSES[4:])


def check(answer: str, accepted: list[str], lemmas: list, index: dict, units: dict) -> Result:
    """answer — ответ ученика; accepted — верные написания; lemmas — лемма каждого токена
    первого написания; index — форма → леммы (engine.form_index)."""
    got = normalize(answer)
    sample = accepted[0]
    if not got:
        return Result("error", "empty", "dontknow", lemma=None, sample=sample,
                      explanation_ru="Ответа нет. Посмотрите на образец и соберите фразу ещё раз.")
    for i, acc in enumerate(accepted):
        if got == normalize(acc):
            return Result("correct" if i == 0 else "correct_alt", sample=sample)
    exp = normalize(sample)
    # лемма для каждого нормализованного токена образца (сокращений в образце нет)
    exp_lemmas = list(lemmas) if len(lemmas) == len(exp) else [None] * len(exp)

    if sorted(got) == sorted(exp):
        return Result("error", "order", "", lemma=None, got=" ".join(got), expected=sample,
                      confidence="high", sample=sample,
                      explanation_ru="Все слова на месте, но порядок другой. В английском порядок слов "
                                     "задаёт смысл: сначала кто, потом действие, потом остальное.")

    # Ответ — другая фраза (почти нет общих слов): называть ошибку нечестно
    matcher = difflib.SequenceMatcher(a=exp, b=got, autojunk=False)
    shared = sum(b.size for b in matcher.get_matching_blocks())
    if shared == 0 or shared * 3 < len(exp):
        return Result("unsure", "wrong", "", lemma=None, got=" ".join(got), expected=sample, confidence="low",
                      sample=sample, explanation_ru="Ответ заметно отличается от образца — система не может "
                                                    "уверенно назвать ошибку. Сравните с образцом.")
    unknown = [w for w in got if w not in index and w not in exp]
    ops = [op for op in difflib.SequenceMatcher(a=exp, b=got, autojunk=False).get_opcodes() if op[0] != "equal"]
    if not ops:  # pragma: no cover - совпадение уже обработано
        return Result("correct", sample=sample)
    tag, i1, i2, j1, j2 = ops[0]
    # сколько слов расходится всего: две ошибки подряд — один блок замены из 2 слов
    spread = sum(max(b2 - b1, c2 - c1) for _, b1, b2, c1, c2 in ops)
    many = len(ops) > 2 or len(unknown) > 1 or spread > 3
    conf = "low" if many else ("medium" if spread > 1 or unknown else "high")

    def lemma_at(i):
        return exp_lemmas[i] if 0 <= i < len(exp_lemmas) else None

    if tag == "replace" and (i2 - i1) == (j2 - j1):
        e, g = _show(exp[i1]), _show(got[j1])
        lem = lemma_at(i1)
        same_lemma = lem is not None and lem in index.get(g.lower(), [])
        if same_lemma:
            return Result("unsure" if conf == "low" else "error", "form", "form", lemma=lem, got=g, expected=e,
                          confidence=conf, sample=sample,
                          explanation_ru=f"Слово выбрано верно, но нужна другая форма: «{e}», а не «{g}». "
                                         "Форма зависит от того, кто действует и когда.")
        if _edit1(e.lower(), g.lower()):
            return Result("unsure" if conf == "low" else "error", "typo", "typo", lemma=lem, got=g, expected=e,
                          confidence=conf, sample=sample,
                          explanation_ru=f"Похоже на опечатку: «{g}» → «{e}».")
        if g.lower() in index:
            kind_err = "form" if _is_function(lem, units) else "wrong"
            return Result("unsure" if conf == "low" else "error", "wrong", kind_err, lemma=lem, got=g, expected=e,
                          confidence=conf, sample=sample,
                          explanation_ru=f"Здесь нужно «{e}», а не «{g}». Сравните значение слов в подсказке.")
        return Result("unsure", "wrong", "", lemma=None, got=g, expected=e, confidence="low", sample=sample,
                      explanation_ru=f"Слова «{g}» нет в изученном словаре — система не может уверенно "
                                     f"оценить ответ. В образце: «{e}».")
    if tag == "delete":
        miss = exp[i1:i2]
        lem = lemma_at(i1)
        err = "form" if _is_function(lem, units) else "wrong"
        return Result("unsure" if conf == "low" else "error", "missing", err, lemma=lem,
                      expected=" ".join(miss), confidence=conf, sample=sample,
                      explanation_ru=f"Пропущено: «{' '.join(miss)}». Без этого фраза неполная по-английски.")
    if tag == "insert":
        extra = got[j1:j2]
        return Result("unsure" if conf == "low" else "error", "extra", "", lemma=None, got=" ".join(extra),
                      confidence=conf, sample=sample,
                      explanation_ru=f"Лишнее: «{' '.join(extra)}». Уберите его — в этой фразе оно не нужно.")
    # разная длина замены — несколько слов сразу
    return Result("unsure", "wrong", "", lemma=None, got=" ".join(got[j1:j2]), expected=" ".join(exp[i1:i2]),
                  confidence="low", sample=sample,
                  explanation_ru="Ответ заметно отличается от образца — система не может уверенно "
                                 "назвать ошибку. Сравните с образцом.")
