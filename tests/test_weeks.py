from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.curriculum.models import TongueTwister, Week, WeekScene
from apps.learning.models import WeekGoal


class WeekModelTests(TestCase):
    def test_scene_twister_goal(self):
        week = Week.objects.get(level__code="A1", number=1)
        scene = WeekScene.objects.create(week=week, can_do_ru="Я смогу…", mission_ru="…", script=[])
        TongueTwister.objects.create(number=1, week=week, series="sounds", text="[T2]This[/]", source="original")
        user = User.objects.create_user("u@example.com", "s3cret-pass-123")
        WeekGoal.objects.create(user=user, week=week, status="done")
        week.refresh_from_db()
        self.assertEqual(week.scene, scene)
        self.assertEqual(week.twister.number, 1)
        self.assertEqual(week.global_number, 1)
        self.assertEqual(Week.objects.get(level__code="A1+", number=1).global_number, 15)
        with self.assertRaises(IntegrityError):
            WeekGoal.objects.create(user=user, week=week, status="not_yet")
