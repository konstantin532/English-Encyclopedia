"""Persisted trainer evidence: behavior is checked against real content and UTC time."""
import importlib.util
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.accounts.data_rights import export_data
from apps.drills.models import Exercise, PracticeItem
from apps.learning.models import IndependentAttempt, UnitProgress
from apps.learning.trainer_content import UNIT_UIDS
from apps.lexicon.models import LexicalUnit
from tests.runner import ensure_content


@override_settings(EE_VOCABULARY_TRAINER_ENABLED=True)
class TrainerServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('apps.learning.trainer_service'),
                             'The persisted trainer service must exist')
        from apps.learning import trainer_service
        self.svc = trainer_service
        self.user = User.objects.create_user(email='trainer@example.test', password='password')
        self.other = User.objects.create_user(email='other-trainer@example.test', password='password')
        self.now = datetime(2026, 3, 7, 18, tzinfo=timezone.utc)
        self.uid = UNIT_UIDS[0]
        self.unit = LexicalUnit.objects.get(uid=self.uid)

    def enroll(self, **kw):
        return self.svc.enroll(self.user, prerequisites_confirmed=True, **kw)

    def start(self, **kw):
        now = kw.pop('now', self.now)
        session = self.svc.start_encounter(self.user, kw.pop('uid', self.uid), now=now, **kw)
        return self.svc.encounter_view(self.user, session.pk, now=now)

    def action(self, view, action, **kw):
        return self.svc.perform_action(self.user, view['session_id'], view['token'], view['revision'],
                                       action, now=kw.pop('now', self.now), **kw)

    def finish(self, now=None, uid=None, answer='tea'):
        now = now or self.now
        view = self.start(now=now, uid=uid or self.uid)
        if view['phase'] == 'intro':
            view = self.action(view, 'begin', now=now)
        view = self.action(view, 'recall', answer=answer, now=now)
        if view['phase'] == 'recall':
            view = self.action(view, 'reveal', now=now)
            view = self.action(view, 'recall', answer=answer, now=now)
        view = self.action(view, 'continue', now=now)
        return self.action(view, 'apply', answer='A tea, please.', self_rating='good', now=now)

    def progress(self):
        return UnitProgress.objects.get(user=self.user, unit=self.unit)

    def test_flag_off_has_no_new_table_queries_and_anonymous_unavailable(self):
        with override_settings(EE_VOCABULARY_TRAINER_ENABLED=False), self.assertNumQueries(0):
            self.assertEqual(self.svc.legacy_managed_units(self.user), set())
            self.assertEqual(self.svc.dashboard(self.user), {'available': False})
            with self.assertRaises(self.svc.TrainerUnavailable):
                self.svc.enroll(self.user, prerequisites_confirmed=True)
        with self.assertRaises(self.svc.TrainerUnavailable):
            self.svc.enroll(AnonymousUser(), prerequisites_confirmed=True)

    def test_opt_in_prerequisite_preferences_and_existing_progress_preserved(self):
        with self.assertRaises(self.svc.TrainerUnavailable):
            self.start()
        with self.assertRaises(self.svc.TrainerUnavailable):
            self.svc.enroll(self.user)
        for kw in ({'daily_limit': 0}, {'daily_limit': 11}, {'daily_limit': True}, {'timezone_name': 'unknown'}):
            with self.assertRaises(ValueError):
                self.enroll(**kw)
        UnitProgress.objects.create(user=self.user, unit=self.unit, stage=3, correct_count=7,
                                    next_review_at=self.now - timedelta(days=2))
        self.enroll()
        view = self.start()
        self.assertEqual(view['phase'], 'intro')
        self.assertEqual((self.progress().stage, self.progress().correct_count), (3, 7))
        self.assertEqual(self.progress().next_review_at, self.now - timedelta(days=2))

    def test_complete_initial_flow_only_exposure_and_safe_projection(self):
        self.enroll()
        view = self.start()
        self.assertIn('mnemonic', view)
        self.assertNotIn('accepted', str(view))
        view = self.action(view, 'begin')
        for key in ('model', 'examples', 'mnemonic', 'snapshot', 'accepted', 'applications'):
            self.assertNotIn(key, view)
        view = self.action(view, 'recall', answer='  TEA! ')
        self.assertEqual(view['phase'], 'feedback')
        self.assertEqual(view['result']['outcome'], 'correct')
        self.assertEqual(view['result']['scheduling'], 'initial_exposure')
        view = self.action(view, 'continue')
        self.assertEqual(view['phase'], 'application')
        self.assertNotIn('valid_examples', view)
        view = self.action(view, 'apply', answer='My own possible answer', self_rating='hard')
        self.assertEqual(view['phase'], 'complete')
        self.assertEqual(self.progress().stage, 0)
        self.assertEqual(self.progress().next_review_at, self.now + timedelta(days=1))
        attempts = IndependentAttempt.objects.filter(user=self.user, origin='trainer')
        self.assertEqual(attempts.count(), 2)
        self.assertEqual(attempts.get(skill='application').outcome, 'self_reported')
        self.assertEqual(attempts.get(skill='recall').evidence['kind'], 'initial_recall')

    def test_delayed_ladder_alternating_families_and_absence_one_step(self):
        self.enroll()
        self.finish()
        families = []
        now = self.now
        for stage, days in ((1, 1), (2, 3), (3, 7), (4, 14), (4, 14)):
            now = self.progress().next_review_at + timedelta(days=30)
            self.finish(now)
            progress = self.progress()
            self.assertEqual(progress.stage, stage)
            self.assertEqual(progress.next_review_at, now + timedelta(days=days))
            attempt = IndependentAttempt.objects.filter(user=self.user, skill='recall').latest('created_at')
            families.append(attempt.evidence['family_id'])
            self.assertTrue(attempt.evidence['schedule_eligible'])
        self.assertTrue(all(a != b for a, b in zip(families, families[1:])))

    def test_early_practice_does_not_postpone_due_and_restarts_24h_exposure_clock(self):
        self.enroll()
        self.finish()
        due = self.progress().next_review_at
        self.finish(self.now + timedelta(hours=23))
        self.assertEqual(self.progress().next_review_at, due)
        self.finish(due)
        self.assertEqual(self.progress().stage, 0)
        self.assertEqual(self.progress().next_review_at, due + timedelta(days=1))

    def test_hint_and_reveal_sticky_resume_no_verified_credit(self):
        self.enroll()
        self.finish()
        due = self.progress().next_review_at
        view = self.start(now=due)
        view = self.action(view, 'hint', now=due)
        self.assertIn('mnemonic', view)
        resumed = self.svc.encounter_view(self.user, view['session_id'], now=self.now)
        self.assertIn('hint', resumed['assistance'])
        view = self.action(resumed, 'reveal', now=due)
        self.assertIn('model', view)
        view = self.action(view, 'recall', answer='tea', now=due)
        self.assertEqual(view['result']['scheduling'], 'assisted')
        self.assertEqual(self.progress().stage, 0)
        attempt = IndependentAttempt.objects.filter(user=self.user, skill='recall').latest('created_at')
        self.assertEqual(attempt.evidence['assistance'], ['hint', 'reveal'])
        self.assertFalse(attempt.evidence['schedule_eligible'])

    def test_error_two_tries_only_one_penalty_and_unknown_not_error(self):
        self.enroll()
        self.finish()
        UnitProgress.objects.filter(user=self.user).update(stage=3)
        due = self.progress().next_review_at
        view = self.start(now=due)
        view = self.action(view, 'recall', answer='coffee', now=due)
        self.assertEqual(view['phase'], 'recall')
        self.assertNotIn('model', view)
        view = self.action(view, 'recall', answer='water', now=due)
        self.assertEqual(view['phase'], 'feedback')
        self.assertEqual(self.progress().stage, 2)
        self.assertEqual(self.progress().next_review_at, due + timedelta(days=1))
        with self.assertRaises(self.svc.TrainerConflict):
            self.action(view, 'recall', answer='tea', now=due)
        view = self.action(view, 'continue', now=due)
        self.action(view, 'apply', answer='Another valid response', self_rating='good', now=due)
        view = self.start(now=due + timedelta(days=1))
        self.action(view, 'recall', answer='an unlisted answer', now=due + timedelta(days=1))
        self.assertEqual(self.progress().stage, 2)
        self.assertEqual(self.progress().wrong_count, 2)

    def test_spoken_is_self_report_and_text_not_spoken(self):
        self.enroll()
        self.finish()
        due = self.progress().next_review_at
        view = self.start(now=due)
        view = self.action(view, 'recall', mode='spoken', now=due)
        self.assertEqual(view['phase'], 'spoken_compare')
        self.assertIn('model', view)
        view = self.action(view, 'rate_spoken', self_rating='good', now=due)
        self.assertEqual(view['result']['outcome'], 'self_reported')
        self.assertEqual(self.progress().stage, 0)
        latest = IndependentAttempt.objects.filter(user=self.user, skill='recall').latest('created_at')
        self.assertEqual(latest.outcome, 'self_reported')
        self.assertEqual(latest.evidence['mode'], 'spoken')
        initial = IndependentAttempt.objects.filter(user=self.user, skill='recall').earliest('created_at')
        self.assertEqual(initial.evidence['mode'], 'text')

    def test_retry_payload_stale_owner_and_atomic_rollback(self):
        self.enroll()
        view = self.action(self.start(), 'begin')
        result = self.action(view, 'recall', answer='tea')
        self.assertEqual(self.action(view, 'recall', answer='tea'), result)
        self.assertEqual(IndependentAttempt.objects.filter(user=self.user).count(), 1)
        with self.assertRaises(self.svc.TrainerConflict):
            self.action(view, 'recall', answer='coffee')
        with self.assertRaises(self.svc.TrainerUnavailable):
            self.svc.encounter_view(self.other, view['session_id'])
        result = self.action(result, 'continue')
        # Retrying a confirmed earlier command returns the CURRENT projection,
        # never the old feedback model into an application assessment.
        replay = self.action(view, 'recall', answer='tea')
        self.assertEqual(replay['phase'], 'application')
        self.assertNotIn('model', replay)
        with patch('apps.learning.models.IndependentAttempt.save', side_effect=RuntimeError('write failed')):
            with self.assertRaises(RuntimeError):
                self.action(result, 'apply', answer='test', self_rating='good')
        self.assertEqual(self.svc.encounter_view(self.user, result['session_id'], now=self.now), result)
        self.assertEqual(IndependentAttempt.objects.filter(user=self.user).count(), 1)

    def test_daily_budget_local_day_dst_resume_and_overdue_first(self):
        self.enroll(timezone_name='America/New_York', daily_limit=1)
        view = self.start()
        self.assertEqual(self.start()['session_id'], view['session_id'])
        with self.assertRaises(self.svc.TrainerLimit):
            self.start(uid=UNIT_UIDS[1])
        self.finish()
        # DST spring day is 23h; UTC due still remains 24h from exposure.
        next_local_day = self.now + timedelta(hours=12)
        self.start(uid=UNIT_UIDS[1], now=next_local_day)
        self.assertEqual(self.progress().next_review_at, self.now + timedelta(hours=24))
        board = self.svc.dashboard(self.user, now=self.now + timedelta(days=3))
        self.assertEqual(board['units'][0]['uid'], self.uid)
        self.assertEqual(board['units'][0]['state'], 'due')

    def test_snapshot_frozen_drafts_expire_without_losing_confirmed_history(self):
        self.enroll()
        view = self.action(self.start(), 'begin')
        view = self.action(view, 'save_draft', answer='private unfinished words')
        with patch('apps.learning.trainer_service.pilot_content', side_effect=ValueError('new invalid content')):
            self.assertEqual(self.svc.encounter_view(self.user, view['session_id'], now=self.now)['draft'], 'private unfinished words')
            view = self.action(view, 'recall', answer='tea')
        view = self.action(view, 'continue')
        view = self.action(view, 'save_draft', answer='old draft')
        from apps.learning.models import TrainerSession
        TrainerSession.objects.filter(pk=view['session_id']).update(draft_updated_at=self.now - timedelta(days=31))
        call_command('expire_trainer_drafts', now=self.now.isoformat(), verbosity=0)
        session = TrainerSession.objects.get(pk=view['session_id'])
        self.assertEqual(session.draft, '')
        self.assertTrue(session.snapshot)
        self.assertEqual(IndependentAttempt.objects.filter(user=self.user).count(), 1)

    def test_mnemonic_private_export_delete_optout_and_legacy_evidence_excluded(self):
        self.enroll()
        self.finish()
        self.svc.save_mnemonic(self.user, self.uid, '<script>private & plain</script>')
        with self.assertRaises(ValueError):
            self.svc.save_mnemonic(self.user, self.uid, 'x' * 301)
        self.svc.enroll(self.other, prerequisites_confirmed=True)
        self.svc.save_mnemonic(self.other, self.uid, 'other private')
        exported = export_data(self.user)
        self.assertIn('<script>private & plain</script>', str(exported))
        self.assertNotIn('other private', str(exported))
        sessions = exported['tables']['learning.trainersession']
        self.assertNotIn('snapshot', sessions[0])
        self.assertNotIn('receipts', sessions[0])
        self.assertEqual(len(exported['tables']['learning.independentattempt']), 2)
        from apps.learning.evidence import lesson_check_attempts
        self.assertFalse(lesson_check_attempts(self.user).exists())
        self.svc.unenroll(self.user)
        self.assertEqual(self.svc.legacy_managed_units(self.user), set())
        self.assertEqual(IndependentAttempt.objects.filter(user=self.user).count(), 2)
        from apps.learning.models import PersonalMnemonic, TrainerSession
        self.user.delete()
        self.assertFalse(TrainerSession.objects.exists())
        self.assertEqual(PersonalMnemonic.objects.count(), 1)

    def test_legacy_all_entries_skip_only_owned_targets_preserve_history(self):
        from apps.learning.services import record_attempt, record_practice, record_recall, due_progress
        self.enroll()
        self.finish()
        before = self.progress()
        record_recall(self.user, self.unit, 'coffee')
        exercise = Exercise.objects.filter(units=self.unit).first()
        self.assertIsNotNone(exercise)
        record_attempt(self.user, exercise, exercise.answer)
        item = PracticeItem.objects.filter(units=self.unit).first()
        if item:
            record_practice(self.user, item)
        after = self.progress()
        self.assertEqual((before.stage, before.correct_count, before.wrong_count, before.next_review_at),
                         (after.stage, after.correct_count, after.wrong_count, after.next_review_at))
        self.assertEqual(self.user.attempts.count(), 1)
        self.assertFalse(due_progress(self.user).filter(unit=self.unit).exists())
        record_recall(self.other, self.unit, 'tea')
        self.assertEqual(UnitProgress.objects.get(user=self.other, unit=self.unit).stage, 1)

    def test_dont_know_is_not_error_and_can_continue_without_copying(self):
        self.enroll()
        self.finish()
        due = self.progress().next_review_at
        view = self.start(now=due)
        view = self.action(view, 'dont_know', now=due)
        self.assertEqual(view['phase'], 'feedback')
        self.assertEqual(self.progress().wrong_count, 0)
        self.assertEqual(self.progress().next_review_at, due + timedelta(days=1))
        self.assertFalse(view['result']['schedule_eligible'])

    def test_resume_model_exposure_updates_24h_clock_without_changing_revision(self):
        self.enroll()
        complete = self.finish()
        refreshed = self.svc.encounter_view(self.user, complete['session_id'], now=self.now + timedelta(hours=23))
        self.assertEqual(complete['revision'], refreshed['revision'])
        due = self.progress().next_review_at
        self.finish(due)
        self.assertEqual(self.progress().stage, 0)
        self.assertEqual(self.progress().next_review_at, due + timedelta(days=1))

    def test_database_attempt_uniqueness_and_real_rollback_after_schedule_write(self):
        from django.db import IntegrityError, transaction
        self.enroll()
        self.finish()
        due = self.progress().next_review_at
        view = self.start(now=due)
        before = self.progress()
        with patch('apps.learning.models.IndependentAttempt.save', side_effect=RuntimeError('attempt failed')):
            with self.assertRaises(RuntimeError):
                self.action(view, 'recall', answer='tea', now=due)
        after = self.progress()
        self.assertEqual((after.stage, after.next_review_at, after.correct_count),
                         (before.stage, before.next_review_at, before.correct_count))
        self.assertEqual(self.svc.encounter_view(self.user, view['session_id'], now=self.now), view)
        self.action(view, 'recall', answer='tea', now=due)
        attempt = IndependentAttempt.objects.filter(trainer_session_id=view['session_id']).get()
        attempt.pk = None
        attempt.batch_token = 'different-operation-token'
        with self.assertRaises(IntegrityError), transaction.atomic():
            attempt.save(force_insert=True)

    def test_same_family_is_ineligible_and_revision_change_never_rewrites_old_history(self):
        from copy import deepcopy
        from apps.learning.trainer_content import pilot_content
        from apps.learning.models import TrainerSession
        self.enroll()
        initial = self.finish()
        old = IndependentAttempt.objects.filter(user=self.user, skill='recall').get()
        old_evidence = deepcopy(old.evidence)
        doc = pilot_content()
        doc['content_version'] = '1.0.1'
        doc['compatibility']['1.0.1'] = {'change': 'cosmetic', 'assessment_revision': '1',
                                         'compatible_with': ['1.0'], 'task_mapping': {}, 'history_policy': 'preserve'}
        due = self.progress().next_review_at
        with patch('apps.learning.trainer_service.pilot_content', return_value=doc):
            view = self.start(now=due)
        session = TrainerSession.objects.get(pk=view['session_id'])
        self.assertEqual(session.content_version, '1.0.1')
        # A future bank accidentally retaining a family cannot manufacture a new
        # context just by giving the task another ID.
        session.family_id = old.evidence['family_id']
        session.save(update_fields=['family_id'])
        view = self.action(view, 'recall', answer='tea', now=due)
        self.assertEqual(view['result']['scheduling'], 'same_family')
        self.assertEqual(self.progress().stage, 0)
        old.refresh_from_db()
        self.assertEqual(old.evidence, old_evidence)
        self.assertEqual(TrainerSession.objects.get(pk=initial['session_id']).content_version, '1.0')

    def test_legacy_default_evidence_never_counts_as_trainer_recall(self):
        from apps.lessons.models import Lesson
        old = IndependentAttempt.objects.create(user=self.user, lesson=Lesson.objects.get(slug='a1-cafe-order'),
                                                skill='meaning', submitted='tea', outcome='model_match')
        self.enroll()
        self.finish()
        self.assertEqual(self.progress().stage, 0)
        old.refresh_from_db()
        self.assertEqual(old.origin, 'lesson')
        self.assertEqual(old.evidence, {})
        self.assertIsNone(old.target_id)
        self.assertEqual(old.assistance, 'not_stated')
        from apps.learning.evidence import lesson_check_attempts
        self.assertEqual(list(lesson_check_attempts(self.user)), [old])

    def test_daily_rate_bound_rolls_back_rejected_request(self):
        from apps.learning.models import TrainerEnrollment
        self.enroll()
        view = self.start()
        TrainerEnrollment.objects.filter(user=self.user).update(rate_window_at=self.now, rate_count=60)
        with self.assertRaises(self.svc.TrainerLimit):
            self.action(view, 'begin')
        self.assertEqual(self.svc.encounter_view(self.user, view['session_id'], now=self.now), view)

    def test_assessment_revision_change_requires_new_baseline_even_with_mapping(self):
        from apps.learning.trainer_content import pilot_content
        self.enroll()
        self.finish()
        due = self.progress().next_review_at
        self.finish(due)
        old_stage = self.progress().stage
        due = self.progress().next_review_at
        doc = pilot_content()
        doc['content_version'] = '2.0'
        doc['assessment_revision'] = '2'
        doc['compatibility']['2.0'] = {
            'change': 'assessment', 'assessment_revision': '2', 'compatible_with': [],
            'task_mapping': {task['task_id']: task['task_id'] for task in doc['units'][0]['recall_tasks']},
            'history_policy': 'preserve',
        }
        with patch('apps.learning.trainer_service.pilot_content', return_value=doc):
            view = self.start(now=due)
            self.assertEqual(view['phase'], 'intro')
            view = self.action(view, 'begin', now=due)
            view = self.action(view, 'recall', answer='tea', now=due)
            self.assertEqual(self.progress().stage, old_stage)
            self.assertEqual(self.progress().next_review_at, due + timedelta(days=1))
            view = self.action(view, 'continue', now=due)
            self.action(view, 'apply', answer='Tea, please.', self_rating='good', now=due)
            self.finish(self.progress().next_review_at)
        self.assertEqual(self.progress().stage, old_stage + 1)
        self.assertEqual(IndependentAttempt.objects.filter(user=self.user, origin='trainer',
                                                         evidence__assessment_revision='1', skill='recall').count(), 2)

    def test_early_verified_wrong_preserves_stage_and_due_but_records_error(self):
        self.enroll()
        self.finish()
        UnitProgress.objects.filter(user=self.user).update(stage=3)
        before = self.progress()
        view = self.start(now=self.now + timedelta(hours=2))
        view = self.action(view, 'recall', answer='coffee', now=self.now + timedelta(hours=2))
        after = self.progress()
        self.assertEqual((after.stage, after.next_review_at), (before.stage, before.next_review_at))
        self.assertEqual(after.wrong_count, before.wrong_count + 1)
        attempt = IndependentAttempt.objects.filter(user=self.user, skill='recall').latest('created_at')
        self.assertEqual(attempt.evidence['scheduling'], 'early_practice')
        self.assertFalse(attempt.evidence['schedule_eligible'])

    def test_valid_goal_without_target_and_spoken_comparison_never_inflate_counts(self):
        self.enroll()
        uid = 'LX-00285'
        view = self.start(uid=uid)
        view = self.action(view, 'begin')
        view = self.action(view, 'recall', answer='Coffee, please.')
        self.assertEqual(view['result']['outcome'], 'uncertain')
        self.assertTrue(view['result']['goal_achieved'])
        self.assertFalse(view['result']['target_used'])
        progress = UnitProgress.objects.get(user=self.user, unit__uid=uid)
        self.assertEqual((progress.stage, progress.correct_count, progress.wrong_count), (0, 0, 0))
        view = self.action(view, 'continue')
        view = self.action(view, 'reveal_application')
        self.assertGreaterEqual(len(view['valid_examples']), 3)
        self.action(view, 'apply', mode='spoken', self_rating='hard')
        attempt = IndependentAttempt.objects.filter(user=self.user, skill='application').get()
        self.assertEqual(attempt.outcome, 'self_reported')
        self.assertEqual(attempt.evidence['mode'], 'spoken')

    def test_other_owner_cannot_mutate_session_and_new_nonpilot_unit_legacy_unchanged(self):
        from apps.learning.services import record_recall
        self.enroll()
        self.svc.enroll(self.other, prerequisites_confirmed=True)
        view = self.start()
        with self.assertRaises(self.svc.TrainerUnavailable):
            self.svc.perform_action(self.other, view['session_id'], view['token'], view['revision'], 'begin', now=self.now)
        self.assertEqual(self.svc.encounter_view(self.user, view['session_id'], now=self.now), view)
        other_unit = LexicalUnit.objects.exclude(uid__in=UNIT_UIDS).first()
        record_recall(self.user, other_unit, other_unit.lemma)
        self.assertEqual(UnitProgress.objects.get(user=self.user, unit=other_unit).stage, 1)

    def test_local_timezone_now_still_uses_24_elapsed_hours_across_dst(self):
        from zoneinfo import ZoneInfo
        self.enroll(timezone_name='America/New_York')
        local_now = datetime(2026, 3, 7, 18, tzinfo=ZoneInfo('America/New_York'))
        self.start(now=local_now)
        self.assertEqual(self.progress().next_review_at,
                         local_now.astimezone(timezone.utc) + timedelta(hours=24))

    def test_idempotent_model_delivery_records_exposure_and_conflict_state_hides_material(self):
        self.enroll()
        view = self.action(self.start(), 'begin')
        feedback = self.action(view, 'recall', answer='tea')
        application = self.action(feedback, 'continue')
        self.action(application, 'apply', answer='Tea, please.', self_rating='good')
        self.action(application, 'apply', answer='Tea, please.', self_rating='good',
                    now=self.now + timedelta(hours=23))
        due = self.progress().next_review_at
        self.finish(due)
        self.assertEqual(self.progress().stage, 0)
        with self.assertRaises(self.svc.TrainerConflict) as conflict:
            self.action(view, 'recall', answer='coffee', now=due)
        canonical = conflict.exception.canonical
        for field in ('model', 'mnemonic', 'valid_examples', 'result', 'examples'):
            self.assertNotIn(field, canonical)
        self.assertIn('session_id', canonical)
        self.assertIn('revision', canonical)

    def test_legacy_reveal_and_successful_model_return_are_sticky_trainer_help(self):
        import json
        from django.urls import reverse
        self.enroll()
        self.finish()
        due = self.progress().next_review_at
        view = self.start(now=due)
        self.client.force_login(self.user)
        response = self.client.post(reverse('api:recall_unit', args=[self.uid]),
                                    json.dumps({'reveal': True}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        view = self.svc.encounter_view(self.user, view['session_id'], now=due)
        self.assertIn('legacy_model', view['assistance'])
        view = self.action(view, 'recall', answer='tea', now=due)
        self.assertFalse(view['result']['schedule_eligible'])
        self.assertEqual(self.progress().stage, 0)
        view = self.action(view, 'continue', now=due)
        self.action(view, 'apply', answer='Tea, please.', self_rating='good', now=due)
        later = self.progress().next_review_at
        view = self.start(now=later)
        response = self.client.post(reverse('api:recall_unit', args=[self.uid]),
                                    json.dumps({'answer': 'tea'}), content_type='application/json')
        self.assertTrue(response.json()['correct'])
        view = self.svc.encounter_view(self.user, view['session_id'], now=later)
        self.assertIn('legacy_model', view['assistance'])
        self.action(view, 'recall', answer='tea', now=later)
        self.assertEqual(self.progress().stage, 0)

    def test_exercise_and_practice_model_paths_register_help_before_response(self):
        import json
        from django.urls import reverse
        from apps.learning.models import TrainerSession
        self.enroll()
        view = self.action(self.start(uid='LX-00084'), 'begin')
        self.client.force_login(self.user)
        exercise = Exercise.objects.get(lesson__slug='a1-cafe-order', order=1)
        item = PracticeItem.objects.filter(lesson__slug='a1-cafe-order', units__uid='LX-00084').first()
        self.assertIsNotNone(item)
        for endpoint, target in (('api:check_exercise', exercise), ('api:check_practice', item)):
            for payload in ({'reveal': True}, {'answer': target.answer}):
                with self.subTest(endpoint=endpoint, payload=payload):
                    TrainerSession.objects.filter(pk=view['session_id']).update(assistance=[])
                    response = self.client.post(reverse(endpoint, args=[target.pk]), json.dumps(payload),
                                                content_type='application/json')
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('legacy_model', TrainerSession.objects.get(pk=view['session_id']).assistance)

    def test_export_redacts_unfinished_assessment_models_but_keeps_own_evidence_and_completed_history(self):
        from apps.lessons.models import Lesson
        self.enroll()
        completed = self.finish()
        legacy = IndependentAttempt.objects.create(
            user=self.user, lesson=Lesson.objects.get(slug='a1-cafe-order'), skill='meaning',
            submitted='old answer', outcome='model_match', model_snapshot='legacy model remains')
        due = self.progress().next_review_at
        pending = self.start(now=due)
        pending = self.action(pending, 'recall', answer='coffee', now=due)
        self.assertEqual(pending['phase'], 'recall')
        attempt = IndependentAttempt.objects.get(trainer_session_id=pending['session_id'])
        exported = export_data(self.user)['tables']
        sessions = {row['id']: row for row in exported['learning.trainersession']}
        attempts = {row['id']: row for row in exported['learning.independentattempt']}
        hidden_result = sessions[pending['session_id']]['result']
        self.assertNotIn('canonical_answer', hidden_result)
        self.assertNotIn('feedback', hidden_result)
        self.assertEqual(hidden_result['outcome'], 'incorrect')
        self.assertNotIn('model_snapshot', attempts[attempt.pk])
        self.assertEqual(attempts[attempt.pk]['submitted'], 'coffee')
        self.assertEqual(attempts[attempt.pk]['evidence'], attempt.evidence)
        self.assertEqual(sessions[completed['session_id']]['result']['canonical_answer'], 'tea')
        completed_recall = next(row for row in attempts.values()
                                if row['trainer_session_id'] == completed['session_id'] and row['skill'] == 'recall')
        self.assertEqual(completed_recall['model_snapshot'], 'tea')
        self.assertEqual(attempts[legacy.pk]['model_snapshot'], 'legacy model remains')
        # Redaction is an export projection; the stored historical snapshot stays intact.
        attempt.refresh_from_db()
        self.assertEqual(attempt.model_snapshot, 'tea')

    def _historical_delivery_blocks_late_active_credit(self, *, replay):
        self.enroll()
        view = self.action(self.start(), 'begin')
        view = self.action(view, 'recall', answer='tea')
        application = self.action(view, 'continue')
        completed = self.action(application, 'apply', answer='Tea, please.', self_rating='good')
        due = self.progress().next_review_at
        active = self.start(now=due)
        if replay:
            self.action(application, 'apply', answer='Tea, please.', self_rating='good', now=due)
        else:
            self.svc.encounter_view(self.user, completed['session_id'], now=due)
        # Let the exposure clock age past 24h while keeping the same assessment
        # open. Registered history help must remain sticky, not merely a delay.
        later = due + timedelta(hours=25)
        result = self.action(active, 'recall', answer='tea', now=later)
        self.assertFalse(result['result']['schedule_eligible'])
        self.assertEqual(result['result']['scheduling'], 'assisted')
        self.assertIn('history_model', result['assistance'])
        self.assertEqual(self.progress().stage, 0)

    def test_historical_get_help_stays_sticky_after_24h_on_open_assessment(self):
        self._historical_delivery_blocks_late_active_credit(replay=False)

    def test_historical_replay_help_stays_sticky_after_24h_on_open_assessment(self):
        self._historical_delivery_blocks_late_active_credit(replay=True)

    def test_wrong_and_unknown_recall_do_not_promote_new_to_recognition(self):
        self.enroll()
        view = self.action(self.start(), 'begin')
        view = self.action(view, 'recall', answer='coffee')
        self.assertEqual(self.progress().status, 'new')
        self.action(view, 'recall', answer='unlisted words')
        self.assertEqual(self.progress().status, 'new')

    def test_spoken_self_report_does_not_promote_new_to_recognition(self):
        self.enroll()
        view = self.action(self.start(), 'begin')
        view = self.action(view, 'recall', mode='spoken')
        self.action(view, 'rate_spoken', self_rating='good')
        self.assertEqual(self.progress().status, 'new')

    def test_helped_correct_recall_does_not_promote_new_to_recognition(self):
        self.enroll()
        view = self.action(self.start(), 'begin')
        view = self.action(view, 'hint')
        self.action(view, 'recall', answer='tea')
        self.assertEqual(self.progress().status, 'new')

    def test_unaided_correct_recall_can_promote_only_new_to_recognition(self):
        self.enroll()
        self.finish()
        self.assertEqual(self.progress().status, 'recognition')
        UnitProgress.objects.filter(user=self.user, unit=self.unit).update(status='active')
        self.finish(self.progress().next_review_at)
        self.assertEqual(self.progress().status, 'active')

    def test_help_comparison_preserves_typed_draft_and_legacy_receipt_fingerprint(self):
        import hashlib
        import json
        from apps.learning.models import TrainerSession
        self.enroll()
        view = self.action(self.start(), 'begin')
        old = view
        view = self.action(view, 'hint', answer='My typed idea')
        self.assertEqual(view['draft'], 'My typed idea')
        expected = hashlib.sha256(json.dumps([old['revision'], 'hint', 'My typed idea', 'text', ''],
                                            ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(TrainerSession.objects.get(pk=view['session_id']).receipts[old['token']]['fingerprint'], expected)
        self.assertEqual(self.action(old, 'hint', answer='My typed idea')['revision'], view['revision'])
        view = self.action(view, 'reveal')  # Historical callers omit answer; do not erase a saved draft.
        self.assertEqual(view['draft'], 'My typed idea')
        view = self.action(view, 'recall', mode='spoken', answer='Typed alternative')
        self.assertEqual(view['draft'], 'Typed alternative')
        view = self.action(view, 'rate_spoken', self_rating='hard')
        view = self.action(view, 'continue')
        view = self.action(view, 'reveal_application', answer='A different useful response')
        self.assertEqual(view['draft'], 'A different useful response')
