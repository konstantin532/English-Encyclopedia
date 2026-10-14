"""Текстовая разметка учебных единиц.

Формат из мастер-промпта: [S1-#d32f2f]word[/] — буква категории, номер
класса и (необязательно) HEX. HEX сверяется с реестром: если он не совпадает,
это ошибка контента, а не повод перекрасить класс.
"""
import re
from dataclasses import dataclass
from html import escape

from django.utils.safestring import mark_safe

from .registry import CATEGORY_BY_CODE, PALETTE

TOKEN = re.compile(r"\[([SDJANTPXCOF])(\d{1,2})(?:-(#[0-9a-fA-F]{6}))?\](.+?)\[/\]", re.S)


@dataclass
class MarkupIssue:
    token: str
    problem: str


def find_issues(text: str) -> list[MarkupIssue]:
    issues = []
    for m in TOKEN.finditer(text):
        code, num, hexcolor, _ = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        cat = CATEGORY_BY_CODE[code]
        numbers = {n for n, _, _ in cat.classes}
        if num not in numbers:
            issues.append(MarkupIssue(m.group(0), f"класса {code}{num} нет в реестре"))
        elif hexcolor and hexcolor.lower() != PALETTE[num][1]:
            issues.append(MarkupIssue(m.group(0), f"цвет {hexcolor} не совпадает с реестром {PALETTE[num][1]}"))
    leftovers = TOKEN.sub("", text)
    if "[/]" in leftovers:
        issues.append(MarkupIssue("[/]", "закрывающий тег без открывающего"))
    return issues


def _label(code: str, num: int) -> str:
    cat = CATEGORY_BY_CODE[code]
    name = next((n for k, n, _ in cat.classes if k == num), "")
    return f"{cat.name_ru}: {name}" if name else cat.name_ru


def render_inline(text: str) -> str:
    """Экранирует HTML и превращает токены в span с маркерами."""
    out, pos = [], 0
    for m in TOKEN.finditer(text):
        out.append(escape(text[pos:m.start()]))
        code, num, word = m.group(1), int(m.group(2)), m.group(4)
        out.append(
            f'<span class="mk" data-cat="{code}" data-cls="{num}" '
            f'data-label="{escape(_label(code, num))}">{escape(word)}</span>'
        )
        pos = m.end()
    out.append(escape(text[pos:]))
    html = "".join(out)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)
    return html


def render_block(text: str) -> str:
    """Мини-формат уроков: абзацы через пустую строку, «> » — английский пример, «- » — список."""
    parts = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().splitlines()
        if all(line.startswith("> ") for line in lines):
            def example(line: str) -> str:
                en, sep, ru = line[2:].partition(" — ")
                tail = f' <span class="ex-ru" lang="ru">— {render_inline(ru)}</span>' if sep else ""
                return f'<p lang="en">{render_inline(en)}{tail}</p>'

            items = "".join(example(line) for line in lines)
            parts.append(f'<div class="example annotated">{items}</div>')
        elif all(line.startswith("- ") for line in lines):
            items = "".join(f"<li>{render_inline(line[2:])}</li>" for line in lines)
            parts.append(f"<ul>{items}</ul>")
        else:
            parts.append(f"<p>{render_inline(' '.join(lines))}</p>")
    return mark_safe("".join(parts))


def strip_markup(text: str) -> str:
    return TOKEN.sub(lambda m: m.group(4), text)
