"""Lesson structure checks without a database or browser."""
from html.parser import HTMLParser
from types import SimpleNamespace as NS

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import reverse


class DisclosureParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.optional = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details' and attrs.get('id') == 'lesson-extra-practice':
            self.optional.append(attrs)


class LessonCoreTemplateTests(SimpleTestCase):
    def page(self, **overrides):
        context = {
            'lesson': NS(slug='a1-nouns-first-words', title='Урок',
                         level=NS(code='A1', slug='a1'), order=1),
            'user': NS(is_authenticated=False),
            'layers': [NS(number=n, title=f'Слой {n}', body='Объяснение')
                       for n in range(1, 8)],
            'a1_guide': {'plain': 'Название предмета', 'steps': [
                {'example_en': 'Hidden duplicate', 'example_ru': 'Дубль'}]},
            'extra_missions': [dict(scene='Сцена', prompt='Вопрос',
                                    example='My book.', title='История')],
            'next_lesson': NS(slug='a1-verb-be', title='Глагол be'),
            'exercises': [NS(pk=n, kind='fill') for n in range(1, 6)],
            'translations': [NS(pk=n, prompt_ru='Переведите') for n in range(1, 6)],
        }
        context.update(overrides)
        return render_to_string('lessons/detail.html', context)

    def test_completion_follows_core_and_precedes_all_extras(self):
        html = self.page()
        self.assertIn('Урок пройден ✓', html)
        positions = [html.index(f'id="{anchor}"') for anchor in
                     ('layer-7', 'practice', 'translate', 'lesson-complete',
                      'lesson-extra-practice', 'spoken-coach')]
        self.assertEqual(positions, sorted(positions))
        optional = html.split('id="lesson-extra-practice"', 1)[1]
        for title in ('Проверка без готовых ответов', 'Речевая мастерская',
                      'Практика в новой ситуации', 'Шесть дополнительных историй'):
            self.assertIn(title, optional)
        self.assertIn('href="/lessons/a1-verb-be/">Следующий урок →', html)

    def test_optional_is_one_closed_disclosure(self):
        html = self.page()
        self.assertIn('Ещё практика (по желанию)', html)
        parser = DisclosureParser()
        parser.feed(html)
        self.assertEqual(len(parser.optional), 1)
        self.assertNotIn('open', parser.optional[0])

    def test_lesson_omits_rhythm_and_speech_reviews_for_all_users(self):
        for authenticated in (False, True):
            with self.subTest(authenticated=authenticated):
                html = self.page(user=NS(is_authenticated=authenticated))
                for text in ('Ритм фразы', 'Умное повторение фраз',
                             'Мои речевые повторения', 'data-speech-tap',
                             'data-speech-review>'):
                    self.assertNotIn(text, html)
                self.assertIn('data-speech-record>', html)

    def test_other_speech_surfaces_keep_optional_controls(self):
        html = render_to_string('components/speech_studio_controls.html', {
            'user': NS(is_authenticated=True),
        })
        for text in ('Ритм фразы', 'Умное повторение фраз', 'Мои речевые повторения'):
            self.assertIn(text, html)

    def test_every_exercise_and_translation_keeps_its_id_and_url(self):
        html = self.page()
        core = html.split('id="lesson-complete"', 1)[0]
        for n in range(1, 6):
            for identity in (f'id="q{n}"', f'id="a{n}"', f'id="t{n}"', f'id="ta{n}"'):
                self.assertIn(identity, core)
            self.assertIn(f'data-url="{reverse("api:check_exercise", args=[n])}"', core)
            self.assertIn(f'data-url="{reverse("api:check_practice", args=[n])}"', core)
        self.assertIn('Задание 5 из 5', core)
        self.assertIn('Перевод 5 из 5', core)

    def test_minute_card_retains_old_anchor_without_duplicate_steps(self):
        html = self.page()
        self.assertIn('id="beginner-steps"', html)
        self.assertIn('Понять за минуту', html)
        self.assertNotIn('Разобрать ещё проще', html)
        self.assertNotIn('Hidden duplicate', html)

    def test_no_extras_or_next_lesson_has_no_empty_disclosure_or_broken_link(self):
        html = self.page(a1_guide=None, extra_missions=None, next_lesson=None)
        self.assertIn('Урок пройден ✓', html)
        self.assertNotIn('id="lesson-extra-practice"', html)
        self.assertNotIn('href="#lesson-extra-practice"', html)
        self.assertNotIn('Следующий урок →', html)

    def test_cafe_lab_stays_inside_optional_disclosure(self):
        lesson = NS(slug='a1-cafe-order', title='Кафе',
                    level=NS(code='A1', slug='a1'), order=5)
        html = self.page(lesson=lesson, a1_guide=None, extra_missions=None)
        self.assertLess(html.index('id="lesson-extra-practice"'),
                        html.index('cafe-lab-invite'))
