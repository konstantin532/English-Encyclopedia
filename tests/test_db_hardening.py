"""Укрепление базы: защита истории учеников, ограничения, роль с минимальными правами."""
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from unittest import skipUnless

from apps.core.db_security import POLICY, grant_app_role
from apps.drills.models import Exercise
from apps.learning.models import ExerciseAttempt, MistakeReview, UnitProgress
from apps.lexicon.models import LexicalUnit
from tests.runner import ensure_content


class ProtectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.user = get_user_model().objects.create_user("hard@example.com", password="pw-12345-x")
        cls.exercise = Exercise.objects.filter(lesson__level__code="A1").first()
        ExerciseAttempt.objects.create(user=cls.user, exercise=cls.exercise, answer="x", is_correct=True)

    def test_content_with_learner_history_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.exercise.delete()

    def test_account_deletion_removes_the_learners_own_history(self):
        self.user.delete()
        self.assertFalse(ExerciseAttempt.objects.filter(exercise=self.exercise).exists())

    def test_review_stage_cannot_leave_the_interval_ladder(self):
        unit = LexicalUnit.objects.first()
        with self.assertRaises(IntegrityError), transaction.atomic():
            UnitProgress.objects.create(user=self.user, unit=unit, stage=9)

    def test_mistake_review_counters_stay_within_five_questions(self):
        from django.utils import timezone

        with self.assertRaises(IntegrityError), transaction.atomic():
            MistakeReview.objects.create(user=self.user, exercise=self.exercise, due_at=timezone.now(), current_index=6)


@skipUnless(connection.vendor == "postgresql", "роли и политики RLS есть только в PostgreSQL")
class AppRoleTests(TestCase):
    def test_app_role_gets_policy_on_every_public_table(self):
        with connection.cursor() as cur:
            cur.execute("select 1 from pg_roles where rolname = 'ee_test_app'")
            if cur.fetchone() is None:
                cur.execute("create role ee_test_app nologin")
        tables = grant_app_role("ee_test_app")
        self.assertGreater(tables, 10)
        with connection.cursor() as cur:
            cur.execute("select count(*) from pg_policies where schemaname='public' and policyname=%s", [POLICY])
            self.assertEqual(cur.fetchone()[0], tables)
            cur.execute("select has_table_privilege('ee_test_app', 'public.learning_exerciseattempt', 'DELETE'),"
                        " has_table_privilege('ee_test_app', 'public.learning_exerciseattempt', 'TRUNCATE')")
            self.assertEqual(cur.fetchone(), (True, False))
