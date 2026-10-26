import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from unittest.mock import patch
from datetime import timedelta
from django.test import TransactionTestCase, Client, override_settings
from django.db import connections
from django.utils import timezone
from apps.accounts.models import User
from apps.drills.models import Exercise
from apps.learning.models import SpeechPracticeProgress, MistakeReview
from apps.learning.speech_practice import speech_practice_api
from apps.learning.delayed_review_views import mistake_review
from tests.runner import ensure_content

@override_settings(EE_VOCABULARY_TRAINER_ENABLED=False)
class ConcurrencyAudit(TransactionTestCase):
    # Avoid existing post_migrate receivers requiring apps during flush.
    serialized_rollback = True
    def test_two_domains(self):
        if connections["default"].vendor != "sqlite":
            self.skipTest("Forced read/write overlap is SQLite-specific; PostgreSQL locks before save")
        ensure_content()
        user = User.objects.create_user(email='audit@example.test', password='local-only')
        ex = Exercise.objects.get(lesson__slug='a1-verb-be', order=2)
        speech = SpeechPracticeProgress.objects.create(user=user, content_key='lesson:a1-verb-be', fragment=0)
        review = MistakeReview.objects.create(user=user, exercise=ex, due_at=timezone.now()-timedelta(days=1))
        clients = [Client(raise_request_exception=False), Client(raise_request_exception=False)]
        for client in clients:
            client.force_login(user)
        for model, view, data, row in [
            (SpeechPracticeProgress,speech_practice_api,{'key':speech.content_key,'index':0,'rating':'good'},speech),
            (MistakeReview,mistake_review,{'review_id':review.pk,'index':0,'choice':0},review),
        ]:
            barrier = Barrier(2)
            # Only force the first read/write overlap; retries must re-read freely.
            first_save = local()
            original = model.save
            def synchronized_save(obj,*args,**kwargs):
                if not getattr(first_save, "seen", False):
                    first_save.seen = True
                    barrier.wait(timeout=10)
                return original(obj,*args,**kwargs)
            def request(_):
                try:
                    client = clients[_]
                    path = '/learning/speech-practice/' if model is SpeechPracticeProgress else '/learning/mistake-review/'
                    response = client.post(path,data=json.dumps(data),content_type='application/json') if model is SpeechPracticeProgress else client.post(path,data=data)
                    return response.status_code
                except Exception as error:
                    return type(error).__name__ + ': ' + str(error)
                finally:
                    connections.close_all()
            with patch.object(model,'save',synchronized_save), ThreadPoolExecutor(max_workers=2) as pool:
                result = list(pool.map(request,range(2)))
            row.refresh_from_db()
            print('AUDIT',model.__name__,result,'attempts/index',getattr(row,'attempts',getattr(row,'current_index',None)),flush=True)
            with self.subTest(domain=model.__name__):
                self.assertEqual(sorted(result), [200, 200] if model is SpeechPracticeProgress else [200, 400])
                self.assertEqual(row.attempts if model is SpeechPracticeProgress else row.current_index, 2 if model is SpeechPracticeProgress else 1)
