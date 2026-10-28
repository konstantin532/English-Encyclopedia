"""Fast learner-text checks: render real A1 sources without a database."""
import re
from html.parser import HTMLParser
from types import SimpleNamespace as NS

import yaml
from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.core.a1_active import active_topics
from apps.learning.understanding import get_guide
from apps.taxonomy.markup import render_block

# A1/A2 are also CEFR labels; other marker prefixes/classes are internal codes.
CODE = re.compile(
    r'\b(?!A[12]\b)[SDJANTPXCOF]\d{1,2}\b'
    r'|(?i:разметк\w*|маркер\w*|код\w*|класс\w*)\s+A[12]\b'
)
DOUBLE_DOT = re.compile(r'\.{2,}')


class TextOnly(HTMLParser):
    def __init__(self, include_collapsed=True):
        super().__init__()
        self.parts = []
        self.suppressed = 0
        self.include_collapsed = include_collapsed

    def handle_starttag(self, tag, attrs):
        # A navigation label and the next paragraph are separate text blocks.
        if tag in ('header', 'main', 'section', 'div', 'p', 'li', 'h1', 'h2', 'h3', 'h4'):
            self.parts.append('\0')
        if tag in ('script', 'style') or (tag == 'details' and not self.include_collapsed):
            self.suppressed += 1
        if not self.suppressed:
            # annotations.js exposes data-label as tooltip text.
            self.parts.extend(value for key, value in attrs if key == 'data-label')

    def handle_endtag(self, tag):
        if tag in ('script', 'style') or (tag == 'details' and not self.include_collapsed):
            self.suppressed -= 1

    def handle_data(self, text):
        if not self.suppressed:
            self.parts.append(text)


def text_only(html, include_collapsed=True):
    parser = TextOnly(include_collapsed)
    parser.feed(str(html))
    return ''.join(parser.parts)


def rendered_lesson(source):
    lesson = NS(**{**source, 'level': NS(code='A1', slug='a1'), 'week': NS(number=source['week'])})
    exercises = [NS(**{**ex, 'pk': n, 'get_stage_display': ex['stage']})
                 for n, ex in enumerate(source.get('exercises', []), 1)]
    translations = [NS(**{**item, 'pk': n})
                    for n, item in enumerate(source.get('practice', []), 1)]
    return render_to_string('lessons/detail.html', {
        'lesson': lesson, 'user': NS(is_authenticated=False),
        'a1_pilot': True, 'a1_guide': get_guide(source['slug']),
        'layers': source['layers'], 'exercises': exercises, 'translations': translations,
        'extra_missions': active_topics()[source['order']]['missions'],
    })


class A1LearnerTextTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lessons = [yaml.safe_load(path.read_text(encoding='utf-8'))
                       for path in sorted((settings.CONTENT_DIR / 'seed_lessons').glob('a1_*.yaml'))]

    def assert_clean(self, source):
        text = text_only(rendered_lesson(source))
        self.assertIsNone(CODE.search(text), f"{source['slug']}: internal code in learner text")
        self.assertIsNone(DOUBLE_DOT.search(text), f"{source['slug']}: doubled ASCII period")

    def test_week_one_has_no_code_leaks_or_double_periods(self):
        for source in self.lessons:
            if source['week'] == 1:
                with self.subTest(slug=source['slug']):
                    self.assert_clean(source)

    def test_all_a1_lessons_have_no_code_leaks_or_double_periods(self):
        self.assertEqual(len(self.lessons), 28)
        for source in self.lessons:
            with self.subTest(slug=source['slug']):
                self.assert_clean(source)

    def test_detector_checks_text_without_confusing_attributes_or_cefr(self):
        text = text_only('<p>Урок A1. <span data-cat="T" data-cls="2">This</span>…</p>')
        self.assertIsNone(CODE.search(text))
        for leak in ('T1', 'T2', 'N3', 'S10', 'A3', 'Разметка A1'):
            self.assertRegex('Разметка ' + leak, CODE)
        self.assertRegex('книгу..', DOUBLE_DOT)
        self.assertNotRegex('книгу…', DOUBLE_DOT)
        self.assertIsNone(CODE.search(text_only('<header>Маркеры</header><main><p>A1</p></main>')))
        self.assertRegex(text_only('<p>Разметка <span>A1</span></p>'), CODE)

    def test_curiosity_is_closed_and_keeps_escaped_content(self):
        html = str(render_block('**Для любопытных:** **Семья.** My family is big. <script>bad</script>'))
        self.assertIn('<details class="lesson-curiosity">', html)
        self.assertIn('<summary>Для любопытных</summary>', html)
        self.assertNotIn(' open', html)
        self.assertIn('My family is big.', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('family', text_only(html, include_collapsed=False))

    def test_week_one_replaces_extra_technical_terms(self):
        forbidden = ('детерминатив', 'местоименное употребление', 'исчисляем',
                     'единственное число', 'подлежащ', 'апостроф', 'падеж')
        for source in self.lessons:
            if source['week'] == 1:
                with self.subTest(slug=source['slug']):
                    text = text_only(rendered_lesson(source)).lower()
                    for term in forbidden:
                        self.assertNotIn(term, text)

    def test_all_a1_explanations_use_plain_words_for_extra_technical_terms(self):
        forbidden = ('детерминатив', 'местоимени', 'местоименное', 'исчисляем',
                     'подлежащ', 'сказуем', 'артикл', 'апостроф', 'герунди',
                     'повелительное наклонение', 'вспомогательный глагол',
                     'фразовый глагол', 'начальная форма', 'начальную форму',
                     'начальной форме', 'придаточн', 'прямого дополнения')
        for source in self.lessons:
            with self.subTest(slug=source['slug']):
                text = text_only(rendered_lesson(source)).lower()
                for term in forbidden:
                    self.assertNotIn(term, text, source['slug'] + ': ' + term)

    def test_plain_marker_labels_preserve_word_color_and_internal_identity(self):
        html = str(render_block("[T1]a[/] [T8]I[/]", plain_labels=True))
        self.assertIn('data-cat="T" data-cls="1"', html)
        self.assertIn('data-cat="T" data-cls="8"', html)
        self.assertIn('>a</span>', html)
        self.assertNotIn("Детерминатив", text_only(html))
        self.assertNotIn("местоимения", text_only(html))
        self.assertIn("Детерминатив", str(render_block("[T1]a[/]")))
