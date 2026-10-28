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
MARKER = re.compile(r"\[[A-Z]\d+[^\]\n]*(?:\]|(?=\n|$))|\[/\]")
OPEN_MARKER = re.compile(r"\[([SDJANTPXCOF])(\d{1,2})(?:-(#[0-9a-fA-F]{6}))?\]")


@dataclass
class MarkupIssue:
    token: str
    problem: str


def find_issues(text: str) -> list[MarkupIssue]:
    issues = []
    opened = []
    for tag in MARKER.finditer(text):
        token = tag.group()
        if token == "[/]":
            if not opened:
                issues.append(MarkupIssue(token, "закрывающий тег без открывающего"))
            else:
                start = opened.pop()
                if not text[start.end():tag.start()].strip():
                    issues.append(MarkupIssue(start.group(), "маркер не содержит текста"))
            continue
        if opened:
            issues.append(MarkupIssue(token, "маркеры не могут быть вложенными"))
        opened.append(tag)
        m = OPEN_MARKER.fullmatch(token)
        if not m:
            issues.append(MarkupIssue(token, "неверный маркер или неизвестная категория"))
            continue
        code, num, hexcolor = m.group(1), int(m.group(2)), m.group(3)
        cat = CATEGORY_BY_CODE[code]
        numbers = {n for n, _, _ in cat.classes}
        if num not in numbers:
            issues.append(MarkupIssue(token, f"класса {code}{num} нет в реестре"))
        elif hexcolor and hexcolor.lower() != PALETTE[num][1]:
            issues.append(MarkupIssue(token, f"цвет {hexcolor} не совпадает с реестром {PALETTE[num][1]}"))
    for tag in opened:
        issues.append(MarkupIssue(tag.group(), "маркер не закрыт"))
    return issues


def _label(code: str, num: int, plain_labels: bool = False) -> str:
    if plain_labels:
        return {
            "S": "Называет человека, вещь или понятие",
            "D": "Помогает рассказать о действии или состоянии",
            "J": "Рассказывает, какой человек или предмет",
            "A": "Уточняет, как, где, когда или насколько",
            "N": "Называет число или порядок",
            "T": "Помогает указать на человека или вещь",
            "P": "Показывает связь с другими словами",
            "X": "Короткое слово-помощник",
            "C": "Соединяет слова или части мысли",
            "O": "Готовая реакция в разговоре",
            "F": "Помогает вести разговор",
        }[code]
    cat = CATEGORY_BY_CODE[code]
    name = next((n for k, n, _ in cat.classes if k == num), "")
    return f"{cat.name_ru}: {name}" if name else cat.name_ru


def render_inline(text: str, plain_labels: bool = False) -> str:
    """Экранирует HTML и превращает токены в span с маркерами."""
    out, pos = [], 0
    for m in TOKEN.finditer(text):
        out.append(escape(text[pos:m.start()]))
        code, num, word = m.group(1), int(m.group(2)), m.group(4)
        out.append(
            f'<span class="mk" data-cat="{code}" data-cls="{num}" '
            f'data-label="{escape(_label(code, num, plain_labels))}">{escape(word)}</span>'
        )
        pos = m.end()
    out.append(escape(text[pos:]))
    html = "".join(out)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)
    return html


def render_block(text: str, plain_labels: bool = False) -> str:
    """Мини-формат уроков: абзацы через пустую строку, «> » — английский пример, «- » — список."""
    def inline(value: str) -> str:
        return render_inline(value, plain_labels=plain_labels)

    parts = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().splitlines()
        if all(line.startswith("> ") for line in lines):
            def example(line: str) -> str:
                en, sep, ru = line[2:].partition(" — ")
                tail = f' <span class="ex-ru" lang="ru">— {inline(ru)}</span>' if sep else ""
                return f'<p lang="en">{inline(en)}{tail}</p>'

            items = "".join(example(line) for line in lines)
            parts.append(f'<div class="example annotated">{items}</div>')
        elif lines[0].startswith("**Для любопытных:** "):
            # Optional nuance uses the same escaped inline format as the lesson.
            content = " ".join(lines).removeprefix("**Для любопытных:** ")
            parts.append(
                '<details class="lesson-curiosity">'
                '<summary>Для любопытных</summary>'
                f'<p>{inline(content)}</p>'
                '</details>'
            )
        elif lines[0].startswith("**Разбор:** "):
            # Вопрос должен быть виден раньше правильного ответа.
            # Нативный details доступен с клавиатуры и без JavaScript.
            parts.append(
                '<details class="lesson-diagnostic-answer">'
                '<summary>Показать разбор после своей попытки</summary>'
                f'<p>{inline(" ".join(lines))}</p>'
                '</details>'
            )
        elif all(line.startswith("- ") for line in lines):
            items = "".join(f"<li>{inline(line[2:])}</li>" for line in lines)
            parts.append(f"<ul>{items}</ul>")
        else:
            parts.append(f"<p>{inline(' '.join(lines))}</p>")
    return mark_safe("".join(parts))


def strip_markup(text: str) -> str:
    return TOKEN.sub(lambda m: m.group(4), text)
