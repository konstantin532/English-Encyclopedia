"""Real concurrent transactions, separate connections; no sequential race stand-ins."""
import importlib.util
import json
import threading
from datetime import datetime, timedelta, timezone

from django.db import close_old_connections, connection, connections
from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.drills.models import Exercise
from apps.learning.models import IndependentAttempt, UnitProgress
from tests.runner import ensure_content


@override_settings(EE_VOCABULARY_TRAINER_ENABLED=True)
class TrainerConcurrencyTests(TransactionTestCase):
    # Snapshot rollback also avoids the repository post_migrate receiver, whose
    # required apps argument is not provided by Django flush. No production fix.
    serialized_rollback = True

    def setUp(self):
        if connection.vendor not in ('sqlite', 'postgresql'):
            self.skipTest('Real race fixture supports SQLite and PostgreSQL only')
        self.assertIsNotNone(importlib.util.find_spec('apps.learning.trainer_service'))
        from apps.learning import trainer_service
        self.svc = trainer_service
        ensure_content()
        self.user = User.objects.create_user(email='concurrent-trainer@example.test', password='password')
        self.now = datetime(2026, 3, 7, 18, tzinfo=timezone.utc)
        self.svc.enroll(self.user, prerequisites_confirmed=True)

    def run_race(self, *functions):
        barrier = threading.Barrier(len(functions))
        results, errors, connection_ids = [], [], []
        guard = threading.Lock()

        def worker(fn):
            close_old_connections()
            try:
                connections['default'].ensure_connection()
                with guard:
                    connection_ids.append(id(connections['default'].connection))
                barrier.wait(timeout=10)
                value = fn()
                with guard:
                    results.append(value)
            except Exception as exc:
                with guard:
                    errors.append(exc)
            finally:
                connections['default'].close()

        threads = [threading.Thread(target=worker, args=(fn,), daemon=True) for fn in functions]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertFalse(any(t.is_alive() for t in threads), 'Concurrent operation exceeded bounded join')
        self.assertEqual(len(set(connection_ids)), len(functions))
        return results, errors

    def action(self, view, action, **kw):
        return self.svc.perform_action(self.user, view['session_id'], view['token'], view['revision'],
                                       action, now=kw.pop('now', self.now), **kw)

    def due_view(self, uid='LX-00055', answer='tea'):
        session = self.svc.start_encounter(self.user, uid, now=self.now)
        view = self.svc.encounter_view(self.user, session.pk, now=self.now)
        view = self.action(view, 'begin')
        view = self.action(view, 'recall', answer=answer)
        view = self.action(view, 'continue')
        self.action(view, 'apply', answer='A tea, please.', self_rating='good')
        self.now += timedelta(days=1)
        session = self.svc.start_encounter(self.user, uid, now=self.now)
        return self.svc.encounter_view(self.user, session.pk, now=self.now)

    def test_duplicate_recall_one_attempt_and_one_stage_advance(self):
        view = self.due_view()
        results, errors = self.run_race(*(lambda: self.action(view, 'recall', answer='tea') for _ in range(2)))
        self.assertEqual(errors, [])
        self.assertEqual(results[0], results[1])
        self.assertEqual(IndependentAttempt.objects.filter(trainer_session_id=view['session_id'], skill='recall').count(), 1)
        self.assertEqual(UnitProgress.objects.get(user=self.user, unit__uid='LX-00055').stage, 1)

    def test_reveal_submit_race_never_credit_after_registered_reveal(self):
        view = self.due_view()
        results, errors = self.run_race(lambda: self.action(view, 'reveal'),
                                       lambda: self.action(view, 'recall', answer='tea'))
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], self.svc.TrainerConflict)
        canonical = self.svc.encounter_view(self.user, view['session_id'], now=self.now)
        if 'reveal' in canonical['assistance']:
            self.assertEqual(UnitProgress.objects.get(user=self.user, unit__uid='LX-00055').stage, 0)
            canonical = self.action(canonical, 'recall', answer='tea')
            self.assertFalse(canonical['result']['schedule_eligible'])
        else:
            self.assertEqual(canonical['phase'], 'feedback')
            self.assertEqual(UnitProgress.objects.get(user=self.user, unit__uid='LX-00055').stage, 1)

    def test_concurrent_start_daily_limit_and_same_unit_resume(self):
        self.svc.enroll(self.user, prerequisites_confirmed=True, daily_limit=1)
        results, errors = self.run_race(
            lambda: self.svc.start_encounter(self.user, 'LX-00055', now=self.now),
            lambda: self.svc.start_encounter(self.user, 'LX-00285', now=self.now))
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], self.svc.TrainerLimit)
        uid = results[0].unit.uid
        results, errors = self.run_race(*(lambda: self.svc.start_encounter(self.user, uid, now=self.now) for _ in range(2)))
        self.assertEqual(errors, [])
        self.assertEqual(results[0].pk, results[1].pk)

    def test_legacy_http_transaction_racing_trainer_preserves_queue_and_schedule(self):
        view = self.due_view('LX-00084', 'Sorry? Can you say it again, please?')
        exercise = Exercise.objects.filter(lesson__slug='a1-cafe-order', units__uid='LX-00084').first()
        self.assertIsNotNone(exercise)
        # Exercise history and its 48h queue remain atomic while lexical target
        # progress is managed only by the trainer, across the full HTTP boundary.
        client = Client()
        client.force_login(self.user)
        results, errors = self.run_race(
            lambda: client.post(reverse('api:check_exercise', args=[exercise.pk]),
                                json.dumps({'answer': 'definitely incorrect'}), content_type='application/json'),
            lambda: self.action(view, 'recall', answer='Sorry? Can you say it again, please?'))
        self.assertEqual(errors, [])
        response = next(r for r in results if hasattr(r, 'status_code'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['retry_count'], 5)
        self.assertEqual(self.user.attempts.count(), 1)
        self.assertEqual(self.user.mistake_reviews.count(), 1)
        self.assertEqual(UnitProgress.objects.get(user=self.user, unit__uid='LX-00084').stage, 1)

    def test_draft_cleanup_uses_same_user_gate_and_retries_a_live_writer(self):
        from io import StringIO
        from django.core.management import call_command
        from django.db import transaction
        from django.db.models import F
        from apps.learning.models import TrainerSession
        session = self.svc.start_encounter(self.user, 'LX-00055', now=self.now)
        TrainerSession.objects.filter(pk=session.pk).update(
            draft='expired unsent text', draft_updated_at=self.now - timedelta(days=31))
        started, finished = threading.Event(), threading.Event()
        errors = []

        def cleanup():
            close_old_connections()
            started.set()
            try:
                call_command('expire_trainer_drafts', now=self.now.isoformat(), stdout=StringIO())
            except Exception as exc:
                errors.append(exc)
            finally:
                finished.set()
                connections['default'].close()

        with transaction.atomic():
            if connection.vendor == 'sqlite':
                User.objects.filter(pk=self.user.pk).update(id=F('id'))
            else:
                User.objects.select_for_update().get(pk=self.user.pk)
            thread = threading.Thread(target=cleanup, daemon=True)
            thread.start()
            self.assertTrue(started.wait(timeout=10))
            finished_while_locked = finished.wait(timeout=0.05)
        thread.join(timeout=10)
        self.assertFalse(thread.is_alive())
        self.assertFalse(finished_while_locked, 'Cleanup must wait for the same user operation boundary')
        self.assertEqual(errors, [])
        self.assertEqual(TrainerSession.objects.get(pk=session.pk).draft, '')


class TrainerMigrationPreservationTests(TransactionTestCase):
    """Migrate backwards/forwards only in Django's disposable test database."""
    serialized_rollback = True

    def test_additive_migration_keeps_legacy_attempt_and_schedule_unchanged(self):
        from django.db.migrations.executor import MigrationExecutor
        ensure_content()
        previous = ('learning', '0012_protect_learner_history_and_ranges')
        target = ('learning', '0013_vocabulary_trainer')
        executor = MigrationExecutor(connection)
        executor.migrate([previous])
        try:
            old_apps = executor.loader.project_state([previous]).apps
            OldUser = old_apps.get_model('accounts', 'User')
            OldLesson = old_apps.get_model('lessons', 'Lesson')
            OldUnit = old_apps.get_model('lexicon', 'LexicalUnit')
            OldAttempt = old_apps.get_model('learning', 'IndependentAttempt')
            OldProgress = old_apps.get_model('learning', 'UnitProgress')
            user = OldUser.objects.create(email='migration-legacy@example.test')
            lesson = OldLesson.objects.get(slug='a1-cafe-order')
            unit = OldUnit.objects.get(uid='LX-00055')
            old = OldAttempt.objects.create(user=user, lesson=lesson, skill='meaning', submitted='tea',
                                             outcome='model_match', prompt_snapshot='original prompt', model_snapshot='tea')
            due = datetime(2026, 3, 8, 18, tzinfo=timezone.utc)
            progress = OldProgress.objects.create(user=user, unit=unit, stage=3, next_review_at=due,
                                                   correct_count=9, wrong_count=2, contexts_used=['old-context'])
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate([target])
        saved = IndependentAttempt.objects.get(pk=old.pk)
        self.assertEqual((saved.submitted, saved.prompt_snapshot, saved.model_snapshot), ('tea', 'original prompt', 'tea'))
        self.assertEqual((saved.origin, saved.evidence, saved.assistance), ('lesson', {}, 'not_stated'))
        self.assertIsNone(saved.trainer_session_id)
        self.assertIsNone(saved.target_id)
        progress = UnitProgress.objects.get(pk=progress.pk)
        self.assertEqual((progress.stage, progress.next_review_at, progress.correct_count, progress.wrong_count,
                          progress.contexts_used), (3, due, 9, 2, ['old-context']))
