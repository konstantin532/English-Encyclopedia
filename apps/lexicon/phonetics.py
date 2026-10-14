"""Русская транскрипция по американскому IPA.

Русские буквы — приблизительная подсказка рядом с точным IPA. Трудные звуки,
которых нет в русском, помечаются ключом подсказки (см. HINTS), ударение — знаком ́.
Таблица одна на весь курс, поэтому одно и то же слово везде записано одинаково.
"""
import re
from dataclasses import dataclass

from django.utils.html import escape, format_html_join
from django.utils.safestring import SafeString, mark_safe

STRESS = "́"

HINTS: dict[str, tuple[str, str]] = {
    "dh": ("th звонкий", "кончик языка между зубами, с голосом"),
    "th": ("th глухой", "кончик языка между зубами, без голоса"),
    "w": ("w", "губы трубочкой, быстро разжать"),
    "r": ("американское r", "кончик языка загнут назад и не касается нёба"),
    "ae": ("широкое э", "рот открыт широко, почти «а»"),
    "flap": ("t между гласными", "быстрое лёгкое «д»"),
    "h": ("h", "лёгкий выдох, без хрипа"),
    "ng": ("ng", "звук идёт через нос, задняя часть языка прижата к нёбу"),
}

# Как трудный звук выглядит в русской записи — для памятки
HINT_LETTERS = {"dh": "з", "th": "с", "w": "у", "r": "р, эр", "ae": "э", "flap": "д", "h": "х", "ng": "н"}
IPA_OF_HINT = {"dh": "ð", "th": "θ", "w": "w", "r": "r, ɚ", "ae": "æ", "flap": "t̬", "h": "h", "ng": "ŋ"}

# символ IPA → (русские буквы, гласный ли, ключ подсказки)
_VOWELS: dict[str, tuple[str, str | None]] = {
    "aɪ": ("ай", None), "eɪ": ("эй", None), "oʊ": ("оу", None), "aʊ": ("ау", None), "ɔɪ": ("ой", None),
    "ju": ("ю", None), "jʊ": ("ю", None),
    "ɚ": ("эр", "r"), "ɝ": ("эр", "r"),
    "æ": ("э", "ae"), "ʌ": ("а", None), "ɑ": ("а", None), "a": ("а", None), "ɔ": ("о", None), "o": ("о", None),
    "ə": ("э", None), "e": ("э", None), "ɛ": ("э", None), "ɜ": ("э", None),
    "ɪ": ("и", None), "i": ("и", None), "ʊ": ("у", None), "u": ("у", None),
}
_CONSONANTS: dict[str, tuple[str, str | None]] = {
    "t̬": ("д", "flap"), "dʒ": ("дж", None), "tʃ": ("ч", None),
    "b": ("б", None), "d": ("д", None), "f": ("ф", None), "g": ("г", None), "ɡ": ("г", None),
    "h": ("х", "h"), "k": ("к", None), "l": ("л", None), "m": ("м", None), "n": ("н", None),
    "p": ("п", None), "s": ("с", None), "t": ("т", None), "v": ("в", None), "z": ("з", None),
    "w": ("у", "w"), "r": ("р", "r"), "j": ("й", None),
    "ð": ("з", "dh"), "θ": ("с", "th"), "ʃ": ("ш", None), "ʒ": ("ж", None), "ŋ": ("н", "ng"),
}
_KEEP = {" ", "‿", "|", ",", "-", "—"}
_SILENT = {"ˌ", "ː", ".", "/"}
_TOKENS = sorted([*_VOWELS, *_CONSONANTS], key=len, reverse=True)
_SLASHED = re.compile(r"/([^/]*)/")


@dataclass(frozen=True)
class Seg:
    text: str
    hint: str | None = None


def _parts(source: str):
    """Пары (текст, это ли IPA). Без косых черт вся строка считается IPA."""
    if "/" not in source:
        yield source, True
        return
    pos = 0
    for m in _SLASHED.finditer(source):
        if m.start() > pos:
            yield source[pos:m.start()], False
        yield m.group(1), True
        pos = m.end()
    if pos < len(source):
        yield source[pos:], False


def _scan(ipa: str):
    """Токены IPA: (символ, (буквы, гласный, подсказка)) или (символ, None) для служебных/неизвестных."""
    i = 0
    while i < len(ipa):
        for tok in _TOKENS:
            if ipa.startswith(tok, i):
                if tok in _VOWELS:
                    letters, hint = _VOWELS[tok]
                    yield tok, (letters, True, hint)
                else:
                    letters, hint = _CONSONANTS[tok]
                    yield tok, (letters, False, hint)
                i += len(tok)
                break
        else:
            yield ipa[i], None
            i += 1


def transcribe(source: str) -> list[Seg]:
    segs: list[Seg] = []
    for text, is_ipa in _parts(source or ""):
        if not is_ipa:
            segs.append(Seg(text))
            continue
        stress = False
        for tok, info in _scan(text):
            if info is None:
                if tok == "ˈ":
                    stress = True
                elif tok in _KEEP:
                    segs.append(Seg(tok))
                continue  # служебные знаки и неизвестные символы не выводим
            letters, vowel, hint = info
            if vowel and stress:
                letters = letters[0] + STRESS + letters[1:]
                stress = False
            segs.append(Seg(letters, hint))
    return segs


def to_plain(source: str) -> str:
    return "".join(s.text for s in transcribe(source))


def unknown_symbols(source: str) -> set[str]:
    found: set[str] = set()
    for text, is_ipa in _parts(source or ""):
        if is_ipa:
            found |= {tok for tok, info in _scan(text) if info is None and tok not in _KEEP | _SILENT | {"ˈ"}}
    return found


def render_html(source: str, override: str = "") -> SafeString:
    """HTML русской транскрипции. Ручной вариант (override) выводится как есть, без разметки звуков."""
    if override:
        return format_html_join("", '<span class="ru-tr" lang="ru">[{}]</span>', [(override,)])
    segs = transcribe(source)
    if not segs:
        return mark_safe("")
    inner = []
    for s in segs:
        if s.hint:
            label, tip = HINTS[s.hint]
            title = escape(f"{label}: {tip}")
            inner.append(f'<span class="snd" data-snd="{s.hint}" title="{title}" tabindex="0">{escape(s.text)}</span>')
        else:
            inner.append(escape(s.text))
    return mark_safe(f'<span class="ru-tr" lang="ru">[{"".join(inner)}]</span>')
