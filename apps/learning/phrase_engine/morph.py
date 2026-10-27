"""Морфология: 3-е лицо, -ing, прошедшее время, множественное число, a/an.

Порядок источников: 1) формы из словаря (поле forms), 2) поле past из разметки,
3) правило. Всё, что получено только правилом, попадает в список derived —
это кандидаты на проверку редактором.
"""
import re

derived: list[str] = []  # (лемма, что выведено правилом)

VOWEL_IPA = re.compile(r"^[ˈˌ]?(aɪ|aʊ|oʊ|eɪ|ɔɪ|[aeiouɑæʌɔəɛɪʊɝɚ])")


def article(u):
    """a или an по первому звуку американской транскрипции (а не по букве)."""
    ipa = (u.ipa or "").strip("/ ")
    if ipa:
        return "an" if VOWEL_IPA.match(ipa) else "a"
    derived.append(f"{u.lemma}: a/an по букве (нет ipa_us)")
    return "an" if u.lemma[0].lower() in "aeiou" else "a"


def article_for_word(word, units):
    u = units.get(word)
    if u is not None:
        return article(u)
    return "an" if word[0].lower() in "aeiou" else "a"


def _rule_plural(w):
    if re.search(r"(s|x|z|ch|sh)$", w):
        return w + "es"
    if re.search(r"[^aeiou]y$", w):
        return w[:-1] + "ies"
    return w + "s"


def plural(u):
    if u.count == "PL":
        return u.lemma
    if u.lemma == "person":
        return "people"
    for f in u.forms:
        if f != u.lemma and not f.endswith("ing"):
            return f
    derived.append(f"{u.lemma}: мн.ч. по правилу → {_rule_plural(u.lemma)}")
    return _rule_plural(u.lemma)


def third(u):
    for f in u.forms:
        if f.endswith("s") and not f.endswith("ss") or f in ("has", "does", "goes"):
            if not f.endswith("ing"):
                return f
    w = u.lemma
    out = w + "es" if re.search(r"(s|x|z|ch|sh|o)$", w) else (w[:-1] + "ies" if re.search(r"[^aeiou]y$", w) else w + "s")
    derived.append(f"{u.lemma}: 3 л. по правилу → {out}")
    return out


def ing(u):
    for f in u.forms:
        if f.endswith("ing"):
            return f
    w = u.lemma
    if w.endswith("ie"):
        out = w[:-2] + "ying"
    elif w.endswith("e") and not w.endswith("ee"):
        out = w[:-1] + "ing"
    else:
        out = w + "ing"
    derived.append(f"{u.lemma}: -ing по правилу → {out}")
    return out


def past(u):
    if u.past and u.past not in ("reg", "-"):
        return u.past.split("/")[0]
    for f in u.forms:
        if f.endswith("ed"):
            return f
    w = u.lemma
    out = w + "d" if w.endswith("e") else (w[:-1] + "ied" if re.search(r"[^aeiou]y$", w) else w + "ed")
    derived.append(f"{u.lemma}: прош.вр. по правилу → {out}")
    return out


def is_regular(u):
    return u.past == "reg"
