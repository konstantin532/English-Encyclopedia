"""Ученик может скачать все свои данные и удалить аккаунт со всей историей."""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.drills.models import Exercise
from apps.learning.models import ExerciseAttempt, UnitProgress
from tests.runner import ensure_content


class DataRightsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        User = get_user_model()
        cls.user = User.objects.create_user("me@example.com", password="pw-12345-x", display_name="Костя")
        cls.other = User.objects.create_user("other@example.com", password="pw-12345-x")
        exercise = Exercise.objects.filter(lesson__level__code="A1").first()
        ExerciseAttempt.objects.create(user=cls.user, exercise=exercise, answer="mine", is_correct=True)
        ExerciseAttempt.objects.create(user=cls.other, exercise=exercise, answer="theirs", is_correct=False)

    def test_export_contains_only_my_data_and_no_password(self):
        self.client.force_login(self.user)
        response = self.client.get("/accounts/my-data/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        data = json.loads(response.content)
        self.assertEqual(data["profile"]["email"], "me@example.com")
        answers = [row["answer"] for row in data["tables"]["learning.exerciseattempt"]]
        self.assertEqual(answers, ["mine"])
        self.assertNotIn("password", response.content.decode())

    def test_export_preserves_selected_current_level(self):
        from apps.curriculum.models import Level

        level = Level.objects.get(code="A1")
        self.user.current_level = level
        self.user.save(update_fields=["current_level"])
        self.client.force_login(self.user)

        response = self.client.get("/accounts/my-data/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["profile"]["current_level_id"], level.pk)

    def test_export_requires_login(self):
        self.assertEqual(self.client.get("/accounts/my-data/").status_code, 302)

    def test_wrong_password_keeps_the_account(self):
        self.client.force_login(self.user)
        response = self.client.post("/accounts/delete/", {"password": "nope", "confirm": "УДАЛИТЬ"})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_confirmation_word_is_required(self):
        self.client.force_login(self.user)
        self.client.post("/accounts/delete/", {"password": "pw-12345-x", "confirm": ""})
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_delete_removes_account_and_history_but_not_others(self):
        self.client.force_login(self.user)
        response = self.client.post("/accounts/delete/", {"password": "pw-12345-x", "confirm": "УДАЛИТЬ"})
        self.assertContains(response, "Аккаунт удалён")
        self.assertFalse(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.assertFalse(ExerciseAttempt.objects.filter(answer="mine").exists())
        self.assertTrue(ExerciseAttempt.objects.filter(answer="theirs").exists())
        self.assertFalse(UnitProgress.objects.filter(user_id=self.user.pk).exists())

    def test_dashboard_links_to_data_rights(self):
        self.client.force_login(self.user)
        html = self.client.get("/learning/").content.decode()
        self.assertIn('href="/accounts/my-data/"', html)
        self.assertIn('href="/accounts/delete/"', html)
