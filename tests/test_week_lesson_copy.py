"""Lightweight rendering checks for week and lesson copy; no DB or browser."""
from types import SimpleNamespace as NS

import yaml
from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.stories.script import build_lines
from tests.test_a1_learner_text import rendered_lesson

FORBIDDEN = (
    'Это самооценка, а не автоматическая проверка.',
    'Это не проверка произношения.',
    'Это не угадывание кнопкой и не автоматический экзамен по разговорной речи.',
    'Это измерит только темп нажатий, а не качество английского.',
    'Скорость не оценивается',
    'Запись синтезирована и ещё не проверена преподавателем',
    'Они не являются автоматической оценкой речи',
    'Автоматическая оценка произношения не выполняется',
)


class WeekLessonCopyTests(SimpleTestCase):
    def week_page(self, number=1, *, audio=True, verified=False, authenticated=False):
        source = yaml.safe_load((settings.CONTENT_DIR / 'seed_weeks' / f'a1_w{number:02d}.yaml').read_text(encoding='utf-8'))
        tracks = {speed: {'file': f'audio/{speed}.mp3', 'timings': []}
                  for speed in ('very_slow', 'slow', 'natural')}
        tracks['verified'] = verified
        twister = NS(**source['twister'], audio=tracks if audio else {})
        scene = NS(**{**source, 'chunks': NS(all=[])})
        lines, speakers = build_lines(source['script'])
        return render_to_string('curriculum/week.html', {
            'week': NS(pk=number, number=number, situation_ru='Знакомство', theme_ru='Знакомство',
                       level=NS(code='A1', slug='a1', weeks=14)),
            'scene': scene, 'twister': twister, 'lines': lines, 'speakers': speakers,
            'audio': tracks if audio else {}, 'lessons': [],
            'user': NS(is_authenticated=authenticated),
        })

    def test_all_a1_weeks_omit_disclaimers_and_duplicate_studio(self):
        for n in range(1, 15):
            with self.subTest(week=n):
                html = self.week_page(n)
                for text in FORBIDDEN + ('Интерактивная тренировка звука и речи',
                                        'Речевая мастерская', 'Умное повторение фраз',
                                        'Ритм фразы', 'Послушай → пауза → твоя очередь',
                                        'data-speech-studio', 'data-speech-review',
                                        'data-speech-reference-player'):
                    self.assertNotIn(text, html)

    def test_week_keeps_five_steps_in_order_and_three_speeds(self):
        html = self.week_page()
        headings = ('Послушайте и поймите', 'Попробуйте звук отдельно',
                    'Соберите по кусочкам', 'Целиком, потом быстрее',
                    'Вернитесь к разговору')
        positions = [html.index(f'<h3>{text}</h3>') for text in headings]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(html.count('data-twister-src='), 3)
        for speed in ('very_slow', 'slow', 'natural'):
            self.assertIn(f'data-twister-src="/static/audio/{speed}.mp3"', html)

    def test_week_recorder_is_compact_and_has_one_privacy_note(self):
        for authenticated in (False, True):
            with self.subTest(authenticated=authenticated):
                html = self.week_page(authenticated=authenticated)
                self.assertEqual(html.count('data-speech-recorder>'), 1)
                self.assertEqual(html.count('data-speech-record>Записать себя'), 1)
                self.assertEqual(html.count('Запись не отправляется на сервер.'), 1)
                for attr in ('data-speech-stop', 'data-speech-delete', 'data-speech-playback'):
                    self.assertIn(attr + ' hidden', html)

    def test_only_main_week_player_has_one_short_voice_note(self):
        for verified in (False, True):
            html = self.week_page(verified=verified)
            self.assertEqual(html.count('Голоса созданы нейросетью.'), 1)
            self.assertNotIn('произношение ещё не проверено человеком', html)
            note = html.index('Голоса созданы нейросетью.')
            self.assertLess(html.index('data-story-player'), note)
            self.assertLess(note, html.index('id="twister"'))

    def test_missing_audio_keeps_useful_fallback_and_local_recorder(self):
        html = self.week_page(audio=False)
        self.assertIn('Озвучка этой недели ещё не записана', html)
        self.assertNotIn('Голоса созданы нейросетью.', html)
        self.assertNotIn('data-twister-src=', html)
        self.assertIn('data-speech-recorder>', html)

    def test_all_a1_lessons_keep_one_optional_studio_without_disclaimers(self):
        for path in sorted((settings.CONTENT_DIR / 'seed_lessons').glob('a1_*.yaml')):
            source = yaml.safe_load(path.read_text(encoding='utf-8'))
            with self.subTest(lesson=source['slug']):
                html = rendered_lesson(source)
                for text in FORBIDDEN:
                    self.assertNotIn(text, html)
                self.assertEqual(html.count('data-speech-kind="lesson"'), 1)
                self.assertLess(html.index('id="lesson-extra-practice"'),
                                html.index('data-speech-kind="lesson"'))
                self.assertEqual(html.count('Запись не отправляется на сервер.'), 1)
