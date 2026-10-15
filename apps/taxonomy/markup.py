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
# Проверяем маркеры по отдельности: TOKEN может скрыть вложенный/незакрытый тег.
MARKER_TAG = re.compile(r"\[([SDJANTPXCOF])(\d{1,2})(?:-(#[0-9a-fA-F]{6}))?\]|\[/\]")


@dataclass
class MarkupIssue:
    token: str
    problem: str


def find_issues(text: str) -> list[MarkupIssue]:
    issues = []
    opened = None
    for marker in MARKER_TAG.finditer(text):
        code = marker.group(1)
        if code is None:  # [/]
            if opened is None:
                issues.append(MarkupIssue("[/]", "закрывающий тег без открывающего"))
            opened = None
            continue

        if opened is not None:
            issues.append(MarkupIssue(
                opened.group(0), "открывающий тег без закрывающего (вложенный маркер)"
            ))
        opened = marker

        num = int(marker.group(2))
        hexcolor = marker.group(3)
        cat = CATEGORY_BY_CODE[code]
        numbers = {n for n, _, _ in cat.classes}
        if num not in numbers:
            issues.append(MarkupIssue(marker.group(0), f"класса {code}{num} нет в реестре"))
        elif hexcolor and hexcolor.lower() != PALETTE[num][1]:
            issues.append(MarkupIssue(
                marker.group(0), f"цвет {hexcolor} не совпадает с реестром {PALETTE[num][1]}"
            ))

    if opened is not None:
        issues.append(MarkupIssue(opened.group(0), "открывающий тег без закрывающего"))
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
