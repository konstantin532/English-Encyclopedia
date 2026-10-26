"""HTTP boundary and server rendered trainer: no browser or working database required."""
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from apps.accounts.models import User
from apps.learning import trainer_service as service
from apps.learning.models import IndependentAttempt, TrainerSession
from apps.learning.trainer_content import UNIT_UIDS, PILOT_SLUG
from tests.runner import ensure_content


@override_settings(EE_VOCABULARY_TRAINER_ENABLED=True)
class TrainerViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.user = User.objects.create_user(email='trainer-http@example.test', password='password')
        self.other = User.objects.create_user(email='trainer-other@example.test', password='password')
        self.client.force_login(self.user)
        self.url = '/learning/vocabulary/'

    def start(self):
        service.enroll(self.user, prerequisites_confirmed=True)
        session = service.start_encounter(self.user, UNIT_UIDS[0])
        return service.encounter_view(self.user, session.pk)

    def post(self, view, action, **kw):
        return self.client.post(f'{self.url}{view["session_id"]}/', {
            'token': view['token'], 'revision': view['revision'], 'action': action, **kw})

    def current(self, view):
        return service.encounter_view(self.user, view['session_id'])

    def test_flag_off_all_entry_pages_avoid_new_tables(self):
        paths = [self.url, '/learning/', '/learning/review/', reverse('lexicon:detail', args=[UNIT_UIDS[0]]),
                 reverse('curriculum:week', args=['a1', 3]), reverse('lessons:detail', args=[PILOT_SLUG])]
        with override_settings(EE_VOCABULARY_TRAINER_ENABLED=False), CaptureQueriesContext(connection) as queries:
            responses = [self.client.get(path) for path in paths]
        self.assertEqual(responses[0].status_code, 404)
        for response in responses[1:]:
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'data-trainer-entry')
        self.assertFalse(any(any(name in q['sql'].lower() for name in
            ('learning_trainerenrollment', 'learning_trainersession', 'learning_personalmnemonic')) for q in queries))

    def test_login_csrf_and_opt_in_prerequisite(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        self.assertEqual(csrf.post(self.url, {'action': 'enroll'}).status_code, 403)
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.url), 'Урок 5')
        self.assertEqual(self.client.post(self.url, {'action': 'enroll'}).status_code, 404)
        result = self.client.post(self.url, {'action': 'enroll', 'prerequisites': 'yes', 'daily_limit': '10', 'timezone_name': 'UTC'})
        self.assertEqual(result.status_code, 302)
        self.assertContains(self.client.get(self.url), 'Начать')

    def test_intro_recall_does_not_leak_hidden_answers_and_owner_status(self):
        view = self.start()
        url = f'{self.url}{view["session_id"]}/'
        intro = self.client.get(url)
        self.assertContains(intro, 'Мнемоника')
        self.assertEqual(self.post(view, 'begin').status_code, 302)
        view = self.current(view)
        response = self.client.get(url)
        self.assertNotContains(response, '<span lang="en">tea</span>', html=False)
        self.assertNotContains(response, 'canonical_answer')
        self.assertNotContains(response, 'data-model')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertNotIn('model', self.client.get(url + 'status/').json()['state'])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(url + 'status/').status_code, 404)

    def test_help_preserves_text_and_same_request_is_idempotent_conflict_is_not_grade(self):
        view = self.start(); self.post(view, 'begin'); view = self.current(view)
        response = self.post(view, 'hint', answer='<b>my private thought</b>')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.current(view)['draft'], '<b>my private thought</b>')
        self.assertEqual(self.post(view, 'hint', answer='<b>my private thought</b>').status_code, 302)
        conflict = self.post(view, 'reveal', answer='keep me')
        self.assertEqual(conflict.status_code, 409)
        self.assertContains(conflict, 'keep me', status_code=409)
        self.assertEqual(IndependentAttempt.objects.filter(user=self.user).count(), 0)
        response = self.client.get(f'{self.url}{view["session_id"]}/')
        self.assertContains(response, '&lt;b&gt;my private thought&lt;/b&gt;')

    def test_reveal_to_feedback_spoken_and_open_comparison_are_reachable(self):
        view = self.start(); self.post(view, 'begin'); view = self.current(view)
        self.post(view, 'recall', mode='spoken', answer='typed alternative'); view = self.current(view)
        self.assertEqual(view['phase'], 'spoken_compare')
        self.assertContains(self.client.get(f'{self.url}{view["session_id"]}/'), 'не записывается')
        self.post(view, 'rate_spoken', self_rating='hard'); view = self.current(view)
        self.post(view, 'continue'); view = self.current(view)
        self.post(view, 'reveal_application', answer='my own response'); view = self.current(view)
        self.assertEqual(view['draft'], 'my own response')
        self.assertGreaterEqual(len(view['valid_examples']), 2)
        self.post(view, 'apply', answer='A completely different useful answer.', self_rating='good')
        view = self.current(view)
        self.assertEqual(view['phase'], 'complete')
        self.assertEqual(view['result']['outcome'], 'self_reported')

    def test_unknown_retry_bounds_dont_know_and_mnemonic_escaping(self):
        view = self.start(); self.post(view, 'begin'); view = self.current(view)
        self.post(view, 'reveal', answer='kept'); view = self.current(view)
        self.assertContains(self.client.get(f'{self.url}{view["session_id"]}/'), 'Перейти к разбору')
        self.post(view, 'dont_know'); view = self.current(view)
        self.post(view, 'mnemonic', mnemonic='<script>alert(1)</script>')
        response = self.client.get(f'{self.url}{view["session_id"]}/')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertEqual(self.post(view, 'recall', answer='tea').status_code, 409)

    def test_legacy_material_gets_register_sticky_help(self):
        for path in [reverse('lexicon:detail', args=[UNIT_UIDS[0]]),
                     reverse('curriculum:week', args=['a1', 3]), reverse('lessons:detail', args=[PILOT_SLUG])]:
            view = self.start()
            self.post(view, 'begin'); view = self.current(view)
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn('legacy_model', self.current(view)['assistance'])
            session = TrainerSession.objects.get(pk=view['session_id'])
            session.assistance = []; session.save(update_fields=['assistance'])

    def test_validation_keeps_answer_and_status_does_not_change_revision(self):
        view = self.start(); self.post(view, 'begin'); view = self.current(view)
        response = self.post(view, 'recall', answer='preserve this', mode='invalid')
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'preserve this', status_code=400)
        status = self.client.get(f'{self.url}{view["session_id"]}/status/')
        self.assertEqual(status.json()['state']['revision'], view['revision'])

    def test_unknown_is_not_exact_graded_and_application_follows_comparison(self):
        view = self.start(); self.post(view, 'begin'); view = self.current(view)
        self.post(view, 'recall', answer='A thoughtful unlisted response.'); view = self.current(view)
        self.assertEqual(view['phase'], 'feedback')
        self.assertEqual(view['result']['outcome'], 'uncertain')
        self.post(view, 'continue'); view = self.current(view)
        response = self.client.get(f'{self.url}{view["session_id"]}/')
        self.assertNotContains(response, 'value="apply"')
        self.assertNotContains(response, 'name="self_rating"')
        response = self.post(view, 'reveal_application', answer='A useful alternative', mode='spoken')
        self.assertIn('?mode=spoken', response.url)
        response = self.client.get(response.url)
        self.assertContains(response, 'value="spoken" checked')
        self.assertContains(response, 'value="apply"')

    def test_expired_draft_and_safe_export_links(self):
        from datetime import timedelta
        from django.utils import timezone
        from django.core.management import call_command
        view = self.start(); self.post(view, 'begin'); view = self.current(view)
        self.post(view, 'save_draft', answer='Old private text'); view = self.current(view)
        TrainerSession.objects.filter(pk=view['session_id']).update(draft_updated_at=timezone.now() - timedelta(days=31))
        call_command('expire_trainer_drafts', verbosity=0)
        response = self.client.get(f'{self.url}{view["session_id"]}/')
        self.assertNotContains(response, 'Old private text')
        self.assertContains(response, reverse('accounts:my_data'))
        self.assertContains(response, reverse('accounts:delete_account'))

    def test_valid_csrf_normal_post_works_without_enhancement(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        csrf.get(self.url)
        token = csrf.cookies['csrftoken'].value
        response = csrf.post(self.url, {'action': 'enroll', 'prerequisites': 'yes',
            'daily_limit': '10', 'timezone_name': 'UTC', 'csrfmiddlewaretoken': token})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(service.dashboard(self.user)['enrolled'])

    def test_two_checked_attempts_have_one_retry_and_no_third_attempt(self):
        view = self.start(); self.post(view, 'begin'); view = self.current(view)
        self.post(view, 'recall', answer='coffee'); view = self.current(view)
        self.assertEqual((view['phase'], view['recall_tries']), ('recall', 1))
        self.assertNotIn('model', view)
        self.post(view, 'recall', answer='water'); view = self.current(view)
        self.assertEqual((view['phase'], view['recall_tries']), ('feedback', 2))
        self.assertEqual(self.post(view, 'recall', answer='tea').status_code, 409)
        self.assertEqual(IndependentAttempt.objects.filter(user=self.user, skill='recall').count(), 2)

    def test_existing_review_links_due_pilot_without_claiming_nothing_due(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.learning.models import UnitProgress
        view = self.start()
        UnitProgress.objects.filter(user=self.user).update(next_review_at=timezone.now() - timedelta(days=1))
        response = self.client.get('/learning/review/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.url)
        self.assertContains(response, 'Пора повторить: 1')
        self.assertNotContains(response, 'Сейчас повторять нечего')
        self.assertContains(response, 'В обычной очереди сейчас нет заданий')

    def test_dashboard_model_delivery_registers_sticky_assistance(self):
        view = self.start(); self.post(view, 'begin'); view = self.current(view)
        self.assertEqual(view['assistance'], [])
        response = self.client.get('/learning/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('legacy_model', self.current(view)['assistance'])

    def test_legacy_review_excludes_pilot_future_model_from_upcoming(self):
        view = self.start()
        response = self.client.get('/learning/review/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['upcoming'])
        self.assertNotContains(response, '<span lang="en">tea</span>')
        self.assertContains(response, 'Сроки трёх единиц пилота смотрите в тренажёре')
