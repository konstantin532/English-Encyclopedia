"""Замок курса: материалы только после входа, кроме главной и пробной недели 1.

Остальные тесты открывают страницы без входа (tests/runner.py выключает замок),
поэтому здесь замок включён явно — именно так он работает на сайте.
"""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.drills.models import Exercise
from apps.lessons.models import Lesson
from apps.stories.models import Story
from tests.runner import ensure_content


@override_settings(EE_COURSE_LOGIN_REQUIRED=True)
class CourseLockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.week1_lesson = Lesson.objects.filter(level__code="A1", week__number=1, is_published=True).first()
        cls.week2_lesson = Lesson.objects.filter(level__code="A1", week__number=2, is_published=True).first()
        cls.learner = User.objects.create_user("learner@example.com", "pass-12345")

    def assert_login_wall(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302, url)
        self.assertTrue(response["Location"].startswith(reverse("accounts:login")), url)
        self.assertIn("next=", response["Location"], url)

    def test_public_pages_open_without_login(self):
        for name in ("core:home", "accounts:login", "accounts:signup", "teaching:for_teachers",
                     "taxonomy:legend", "core:healthz", "core:robots"):
            with self.subTest(name=name):
                self.assertNotEqual(self.client.get(reverse(name)).status_code, 302)

    def test_trial_week_one_stays_open(self):
        self.assertEqual(self.client.get(reverse("curriculum:week", args=["a1", 1])).status_code, 200)
        self.assertEqual(self.client.get(reverse("lessons:detail", args=[self.week1_lesson.slug])).status_code, 200)

    def test_course_material_requires_login(self):
        story = Story.objects.filter(is_published=True).first()
        urls = [
            reverse("curriculum:week", args=["a1", 2]),
            reverse("curriculum:level", args=["a1"]),
            reverse("lessons:detail", args=[self.week2_lesson.slug]),
            reverse("lexicon:list"),
            reverse("stories:map"),
            reverse("stories:detail", args=[story.number]),
            reverse("core:classics"),
            reverse("teaching:dashboard"),
            reverse("teaching:join"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assert_login_wall(url)

    def test_login_wall_returns_to_the_requested_page(self):
        url = reverse("curriculum:week", args=["a1", 2])
        response = self.client.get(url)
        self.assertIn("next=" + url, response["Location"])
        login = self.client.post(response["Location"], {"username": "learner@example.com", "password": "pass-12345"})
        self.assertEqual(login["Location"], url)

    def test_learner_sees_closed_material(self):
        self.client.force_login(self.learner)
        self.assertEqual(self.client.get(reverse("curriculum:week", args=["a1", 2])).status_code, 200)
        self.assertEqual(self.client.get(reverse("lessons:detail", args=[self.week2_lesson.slug])).status_code, 200)

    def test_guest_can_check_only_trial_week_exercises(self):
        open_ex = Exercise.objects.filter(lesson=self.week1_lesson).first()
        closed_ex = Exercise.objects.filter(lesson=self.week2_lesson).first()
        ok = self.client.post(reverse("api:check_exercise", args=[open_ex.pk]), "{}", content_type="application/json")
        self.assertNotEqual(ok.status_code, 302)
        self.assert_login_wall(reverse("api:check_exercise", args=[closed_ex.pk]))

    @override_settings(PUBLIC_SITE_URL="https://example.com")
    def test_sitemap_lists_only_open_pages(self):
        body = self.client.get(reverse("core:sitemap")).content.decode()
        self.assertIn(reverse("curriculum:week", args=["a1", 1]), body)
        self.assertIn(reverse("lessons:detail", args=[self.week1_lesson.slug]), body)
        self.assertNotIn(reverse("curriculum:week", args=["a1", 2]), body)
        self.assertNotIn(reverse("lessons:detail", args=[self.week2_lesson.slug]), body)
        self.assertNotIn("/words/", body)


class LockIsOnInRealSettingsTests(TestCase):
    def test_base_settings_default_to_locked(self):
        from config.settings import base
        self.assertTrue(base.EE_COURSE_LOGIN_REQUIRED)

    def test_production_cannot_unlock_the_course(self):
        source = (Path(settings.BASE_DIR) / "config" / "settings" / "production.py").read_text(encoding="utf-8")
        self.assertIn("EE_COURSE_LOGIN_REQUIRED = True", source)

    def test_middleware_is_installed(self):
        self.assertIn("apps.core.access.CourseAccessMiddleware", settings.MIDDLEWARE)
        auth = settings.MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware")
        self.assertGreater(settings.MIDDLEWARE.index("apps.core.access.CourseAccessMiddleware"), auth)


class AuthReadRetryTests(SimpleTestCase):
    """Раннее чтение пользователя переживает временную блокировку SQLite."""

    def make_request(self, outcomes):
        from django.test import RequestFactory
        from django.utils.functional import SimpleLazyObject
        from django.db import OperationalError
        request = RequestFactory().get("/")
        calls = []

        def resolve():
            outcome = outcomes[min(len(calls), len(outcomes) - 1)]
            calls.append(outcome)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        request.user = SimpleLazyObject(resolve)
        return request, calls, OperationalError

    def test_retries_lock_then_succeeds(self):
        from django.db import OperationalError, connection
        from apps.core.access import is_authenticated
        if connection.vendor != "sqlite":
            self.skipTest("повтор нужен только для SQLite")
        lock = OperationalError("database table is locked: accounts_user")
        user = User(email="x@example.com")
        request, calls, _ = self.make_request([lock, lock, user])
        self.assertTrue(is_authenticated(request))
        self.assertEqual(len(calls), 3)

    def test_persistent_lock_gives_503_not_500(self):
        from django.db import OperationalError, connection
        from apps.core.access import AUTH_READ_ATTEMPTS, CourseAccessMiddleware
        if connection.vendor != "sqlite":
            self.skipTest("повтор нужен только для SQLite")
        request, calls, _ = self.make_request([OperationalError("database is locked")])
        request.resolver_match = None
        with override_settings(EE_COURSE_LOGIN_REQUIRED=True):
            response = CourseAccessMiddleware(lambda r: None).process_view(request, lambda r: None, (), {})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(calls), AUTH_READ_ATTEMPTS)

    def test_other_database_errors_are_not_swallowed(self):
        from django.db import OperationalError
        from apps.core.access import is_authenticated
        request, calls, _ = self.make_request([OperationalError("no such table: accounts_user")])
        with self.assertRaises(OperationalError):
            is_authenticated(request)
        self.assertEqual(len(calls), 1)
