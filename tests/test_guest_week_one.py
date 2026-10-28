"""Guest progress uses the authored week-one course fixtures; no browser."""
import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.curriculum.models import Week
from apps.drills.models import Exercise, PracticeItem
from apps.learning.guest_progress import MAX_ITEMS, make_receipt
from apps.learning.models import ExerciseAttempt, ImportedGuestAnswer, UnitProgress, WeekGoal
from apps.lessons.models import Lesson
from tests.runner import ensure_content


class GuestWeekOneTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.week = Week.objects.get(level__code='A1', number=1)
        cls.ex=Exercise.objects.get(lesson__slug='a1-nouns-first-words',order=1)
        cls.practice=PracticeItem.objects.get(lesson__slug='a1-nouns-first-words',order=1)
        cls.unit=cls.ex.units.get()
        cls.practice_unit=cls.practice.units.get()

    def post_answer(self, kind, item, answer):
        name='api:check_exercise' if kind=='exercise' else 'api:check_practice'
        response=self.client.post(reverse(name,args=[item.pk]),json.dumps({'answer':answer}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        return response.json()

    def sign_in(self):
        self.user=User.objects.create_user('guest-import@example.test','strong-test-password-123')
        self.client.force_login(self.user)

    def claim(self,tokens):
        response=self.client.post(reverse('api:import_guest_progress'),json.dumps({'receipts':tokens}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        return response.json()

    def test_guest_can_open_and_answer_both_week_one_lessons(self):
        total=0
        for lesson in Lesson.objects.filter(week=self.week):
            response=self.client.get(reverse('lessons:detail',args=[lesson.slug]))
            self.assertEqual(response.status_code,200)
            self.assertNotIn('Location',response)
            for kind,items in (('exercise',lesson.exercises.all()),('practice',lesson.practice_items.all())):
                for item in items:
                    result=self.post_answer(kind,item,item.answer)
                    self.assertTrue(result['correct'])
                    self.assertFalse(result['saved'])
                    self.assertIn('guest_receipt',result)
                    total+=1
        self.assertLessEqual(total+1,MAX_ITEMS)
        self.assertEqual(ExerciseAttempt.objects.count(),0)
        self.assertEqual(UnitProgress.objects.count(),0)

    def test_valid_guest_result_transfers_once_after_login(self):
        token=self.post_answer('exercise',self.ex,self.ex.answer)['guest_receipt']['token']
        self.sign_in()
        self.assertEqual(self.claim([token])['imported'],1)
        count=UnitProgress.objects.get(user=self.user,unit=self.unit).correct_count
        self.assertEqual(self.claim([token])['imported'],0)
        self.assertEqual(ExerciseAttempt.objects.filter(user=self.user).count(),1)
        self.assertEqual(UnitProgress.objects.get(user=self.user,unit=self.unit).correct_count,count)
        self.assertEqual(ImportedGuestAnswer.objects.filter(user=self.user).count(),1)

    def test_translation_and_goal_transfer_without_replacing_existing_work(self):
        translation=self.post_answer('practice',self.practice,self.practice.answer)['guest_receipt']['token']
        goal=self.client.post(reverse('api:guest_week_goal',args=[self.week.pk]),{'status':'done'}).json()['guest_receipt']['token']
        self.sign_in()
        self.assertEqual(self.claim([translation,goal])['imported'],2)
        self.assertEqual(WeekGoal.objects.get(user=self.user,week=self.week).status,'done')
        self.assertIn(f'{self.practice.lesson.slug}#t{self.practice.order}',UnitProgress.objects.get(user=self.user,unit=self.practice_unit).contexts_used)
        second=self.client.post(reverse('api:guest_week_goal',args=[self.week.pk]),{'status':'not_yet'}).json()['guest_receipt']['token']
        self.assertEqual(self.claim([second])['imported'],0)
        self.assertEqual(WeekGoal.objects.get(user=self.user,week=self.week).status,'done')

    def test_signed_grade_cannot_be_forged_and_stale_content_is_ignored(self):
        token=self.post_answer('exercise',self.ex,self.ex.answer)['guest_receipt']['token']
        self.ex.answer='changed key';self.ex.save(update_fields=['answer'])
        self.sign_in()
        result=self.claim([token,token+'tampered'])
        self.assertEqual(result['imported'],0)
        self.assertEqual(len(result['acknowledged']),2)
        self.assertFalse(ExerciseAttempt.objects.exists())

    def test_expired_results_do_not_apply(self):
        with patch('django.core.signing.time.time',return_value=1):
            token=self.post_answer('exercise',self.ex,self.ex.answer)['guest_receipt']['token']
        self.sign_in()
        self.assertEqual(self.claim([token])['imported'],0)

    def test_later_weeks_and_unverified_answers_do_not_get_receipts(self):
        self.assertIsNone(make_receipt('practice',self.practice,'a different unverified sentence'))
        self.assertIsNone(make_receipt('exercise',self.ex,'x'*201))
        later=Week.objects.get(level=self.week.level,number=2)
        self.ex.lesson.week=later;self.ex.lesson.save(update_fields=['week'])
        self.assertNotIn('guest_receipt',self.post_answer('exercise',self.ex,self.ex.answer))
        self.assertEqual(self.client.post(reverse('api:guest_week_goal',args=[later.pk]),{'status':'done'}).status_code,404)

    def test_import_requires_authentication_and_csrf(self):
        url=reverse('api:import_guest_progress')
        self.assertEqual(self.client.post(url,'{}',content_type='application/json').status_code,302)
        self.sign_in()
        csrf_client=Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(url,'{}',content_type='application/json').status_code,403)
        self.assertEqual(self.client.post(url,json.dumps({'receipts':['x']*(MAX_ITEMS+1)}),content_type='application/json').status_code,400)

    def test_successful_account_answers_are_not_downgraded_by_guest_errors(self):
        token=self.post_answer('exercise',self.ex,'wrong')['guest_receipt']['token']
        self.sign_in()
        self.post_answer('exercise',self.ex,self.ex.answer)
        before=UnitProgress.objects.get(user=self.user,unit=self.unit)
        self.assertEqual(self.claim([token])['imported'],0)
        after=UnitProgress.objects.get(user=self.user,unit=self.unit)
        self.assertEqual((before.stage,before.correct_count,before.wrong_count),(after.stage,after.correct_count,after.wrong_count))

    @override_settings(EE_VOCABULARY_TRAINER_ENABLED=False)
    def test_normal_submissions_and_import_share_the_user_lock_without_trainer(self):
        from apps.learning.trainer_state import run_serialized
        self.sign_in()
        with patch('apps.learning.trainer_state.get_user_model') as model:
            model.return_value._meta.pk.name='id'
            run_serialized(self.user, lambda: None)
            model.return_value.objects.filter.return_value.update.assert_called_once()

    def test_translation_deduplicates_the_exact_task_not_other_contexts(self):
        token=self.post_answer('practice',self.practice,self.practice.answer)['guest_receipt']['token']
        self.sign_in()
        UnitProgress.objects.create(user=self.user,unit=self.practice_unit,contexts_used=['another-lesson#t1'])
        self.assertEqual(self.claim([token])['imported'],1)
        count=UnitProgress.objects.get(user=self.user,unit=self.practice_unit).correct_count
        repeat=make_receipt('practice',self.practice,self.practice.answer)['token']
        self.assertEqual(self.claim([repeat])['imported'],0)
        self.assertEqual(UnitProgress.objects.get(user=self.user,unit=self.practice_unit).correct_count,count)

    def test_signup_rotates_csrf_then_imports_the_guest_result(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.get(reverse('lessons:detail',args=[self.ex.lesson.slug])).status_code,200)
        old_csrf=client.cookies['csrftoken'].value
        result=client.post(reverse('api:check_exercise',args=[self.ex.pk]),json.dumps({'answer':self.ex.answer}),content_type='application/json',HTTP_X_CSRFTOKEN=old_csrf)
        token=result.json()['guest_receipt']['token']
        response=client.post(reverse('accounts:signup'),{'email':'signup-transfer@example.test','password1':'strong-local-signup-pass-123','password2':'strong-local-signup-pass-123'},HTTP_X_CSRFTOKEN=old_csrf)
        self.assertEqual(response.status_code,302)
        new_csrf=client.cookies['csrftoken'].value
        self.assertNotEqual(old_csrf,new_csrf)
        body=json.dumps({'receipts':[token]})
        self.assertEqual(client.post(reverse('api:import_guest_progress'),body,content_type='application/json',HTTP_X_CSRFTOKEN=old_csrf).status_code,403)
        response=client.post(reverse('api:import_guest_progress'),body,content_type='application/json',HTTP_X_CSRFTOKEN=new_csrf)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['imported'],1)
        user=User.objects.get(email='signup-transfer@example.test')
        self.assertFalse(user.markers_enabled)
        self.assertEqual(ExerciseAttempt.objects.filter(user=user).count(),1)

    def test_failed_import_rolls_back_its_receipt_and_can_retry(self):
        token=self.post_answer('exercise',self.ex,self.ex.answer)['guest_receipt']['token']
        self.sign_in()
        with patch('apps.learning.guest_progress.record_attempt',side_effect=RuntimeError('temporary failure')):
            with self.assertRaises(RuntimeError):
                self.claim([token])
        self.assertFalse(ImportedGuestAnswer.objects.exists())
        self.assertFalse(ExerciseAttempt.objects.exists())
        self.assertEqual(self.claim([token])['imported'],1)
