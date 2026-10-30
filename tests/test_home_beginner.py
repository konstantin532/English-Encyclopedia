"""Focused homepage and marker-preference checks; no course loader."""
from importlib import import_module
from types import SimpleNamespace as NS
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.core.context_processors import site


class BeginnerHomeTemplateTests(SimpleTestCase):
    def page(self, authenticated=False):
        return render_to_string('core/home.html', {
            'user': NS(is_authenticated=authenticated), 'MARKERS_MODE': 'off',
            'first_week': NS(number=1, level=NS(slug='a1')),
            'first_lesson': NS(slug='a1-nouns-first-words', level=NS(code='A1'), minutes=40),
            'units_ready': 1047, 'totals': {'units': 6200},
        })

    def test_home_omits_developer_inventory_and_duplicate_examples(self):
        html = self.page()
        for text in ('THE LIVING LANGUAGE ATLAS', 'Одиннадцать линий',
                     'Путь от первого слова до B2+', 'из 6200', '10 классов',
                     'единиц в словаре', 'готовых уроков', 'data-specimen'):
            self.assertNotIn(text, html)
        self.assertEqual(html.count('data-language-atlas>'), 1)
        self.assertIn('14 недель A1 уже готовы', html)
        self.assertIn('Как читать маркеры →', html)
        self.assertIn('href="/markers/"', html)

    def test_guest_primary_action_goes_to_week_one(self):
        html = self.page()
        self.assertIn('href="/levels/a1/weeks/1/">Начать с нуля', html)
        self.assertNotIn('Начать первый урок', html)
        self.assertIn('Продолжить обучение', self.page(authenticated=True))

    def test_guest_defaults_to_no_markers_before_scripts_load(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        context = site(request)
        self.assertEqual(context['MARKERS_MODE'], 'off')
        html = render_to_string('base.html', {**context, 'user': request.user})
        self.assertIn('data-markers="off"', html.split('<head>')[0])
        self.assertNotIn('aria-label="Маркеры в тексте"', html)

    def test_enabled_accounts_keep_color_or_monochrome_choice(self):
        for color, expected in ((True, 'color'), (False, 'mono')):
            request = RequestFactory().get('/')
            request.user = User(markers_in_color=color, markers_enabled=True)
            with patch('apps.learning.models.UnitProgress.objects.filter') as query:
                query.return_value.count.return_value = 0
                self.assertEqual(site(request)['MARKERS_MODE'], expected)

    def test_new_model_default_and_migration_preserve_older_accounts(self):
        self.assertFalse(User().markers_enabled)
        migration = import_module('apps.accounts.migrations.0002_markers_enabled')
        fields = [op.field.default for op in migration.Migration.operations
                  if getattr(op, 'name', '') == 'markers_enabled']
        self.assertEqual(fields, [True, False])


class MarkerPreferenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('marker-test@example.test', 'local-test-pass-123')
        self.client.force_login(self.user)
        self.url = reverse('learning:toggle_markers')

    def test_new_account_starts_without_markers(self):
        self.user.refresh_from_db()
        self.assertFalse(self.user.markers_enabled)

    def test_setting_is_idempotent_and_preserves_color_preference(self):
        self.user.markers_in_color = False
        self.user.save(update_fields=['markers_in_color'])
        for _ in range(2):
            response = self.client.post(self.url, {'enabled': 'true'}, HTTP_X_REQUESTED_WITH='fetch')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['enabled'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.markers_enabled)
        self.assertFalse(self.user.markers_in_color)
        self.client.post(self.url, {'enabled': 'false'}, HTTP_X_REQUESTED_WITH='fetch')
        self.user.refresh_from_db()
        self.assertFalse(self.user.markers_enabled)

    def test_invalid_state_cannot_change_either_preference(self):
        before = (self.user.markers_in_color, self.user.markers_enabled)
        self.assertEqual(self.client.post(self.url, {'enabled': 'maybe'}).status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual((self.user.markers_in_color, self.user.markers_enabled), before)

    def test_legacy_color_toggle_remains_compatible(self):
        response = self.client.post(self.url, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['color'])
