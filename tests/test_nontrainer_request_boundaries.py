"""Request-level contention boundaries; all data lives in Django's test database."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.db import OperationalError, connections
from django.test import Client, TransactionTestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.drills.models import Exercise
from apps.learning.models import MistakeReview, SpeechPracticeProgress
from tests.runner import ensure_content


@override_settings(EE_VOCABULARY_TRAINER_ENABLED=False)
class RequestBoundaries(TransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        ensure_content()
        self.user = User.objects.create_user(email='boundary@example.test', password='local-only')
        exercise = Exercise.objects.get(lesson__slug='a1-verb-be', order=2)
        self.speech = SpeechPracticeProgress.objects.create(user=self.user, content_key='lesson:a1-verb-be', fragment=0)
        self.review = MistakeReview.objects.create(user=self.user, exercise=exercise, due_at=timezone.now()-timedelta(days=1))

    def send(self, client, speech):
        if speech:
            return client.post('/learning/speech-practice/', json.dumps({'key':self.speech.content_key,'index':0,'rating':'good'}),content_type='application/json')
        return client.post('/learning/mistake-review/', {'review_id':self.review.pk,'index':0,'choice':0})

    def test_csrf_rejection_leaves_both_rows_unchanged(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for speech in (True, False):
            self.assertEqual(self.send(client, speech).status_code, 403)
        self.speech.refresh_from_db(); self.review.refresh_from_db()
        self.assertEqual(self.speech.attempts, 0)
        self.assertEqual(self.review.current_index, 0)

    def test_exhausted_sqlite_retries_return_409_without_writes(self):
        if connections['default'].vendor != 'sqlite':
            self.skipTest('SQLite-specific lock retry')
        client = Client(raise_request_exception=False)
        client.force_login(self.user)
        for speech, model in ((True, SpeechPracticeProgress),(False,MistakeReview)):
            locked = sqlite3.OperationalError('database is locked')
            locked.sqlite_errorcode = sqlite3.SQLITE_BUSY
            error = OperationalError('database is locked')
            error.__cause__ = locked
            original_save = model.save
            def save_then_lock(obj, *args, **kwargs):
                original_save(obj, *args, **kwargs)
                raise error
            with patch.object(model, 'save', save_then_lock):
                self.assertEqual(self.send(client, speech).status_code, 409)
        self.speech.refresh_from_db(); self.review.refresh_from_db()
        self.assertEqual(self.speech.attempts, 0)
        self.assertEqual(self.review.current_index, 0)

    @override_settings(EE_VOCABULARY_TRAINER_ENABLED=True)
    def test_trainer_enabled_concurrent_requests_preserve_counts(self):
        clients = [Client(raise_request_exception=False), Client(raise_request_exception=False)]
        for client in clients:
            client.force_login(self.user)
        for speech in (True, False):
            barrier = Barrier(2)
            def worker(index):
                try:
                    barrier.wait(timeout=10)
                    response = self.send(clients[index], speech)
                    if response.status_code == 500 and response.exc_info:
                        import traceback
                        print("".join(traceback.format_exception(*response.exc_info)), flush=True)
                    return response.status_code
                finally:
                    connections.close_all()
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(worker, range(2)))
            self.assertEqual(sorted(results), [200,200] if speech else [200,400])
        self.speech.refresh_from_db(); self.review.refresh_from_db()
        self.assertEqual(self.speech.attempts, 2)
        self.assertEqual(self.review.current_index, 1)
