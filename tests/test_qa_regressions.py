"""Regression tests for malformed input, safe redirects and linguistic markup."""

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.drills.models import Exercise
from apps.lexicon.models import LexicalUnit
from apps.poems.models import Poem
from apps.taxonomy.markup import find_issues


class MarkerRedirectRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="redirect-qa@example.test", password="StrongTest123!A")
        self.client.force_login(self.user)
        self.url = reverse("learning:toggle_markers")

    def test_unsafe_return_urls_fall_back_to_dashboard(self):
        for target in (
            "https://outside.example/steal",
            "//outside.example/steal",
            "http://testserver.attacker.example/steal",
            "javascript:alert(1)",
        ):
            with self.subTest(target=target):
                response = self.client.post(self.url, {"next": target})
                self.assertRedirects(response, reverse("learning:dashboard"), fetch_redirect_response=False)

    def test_internal_return_path_is_preserved(self):
        response = self.client.post(self.url, {"next": "/words/?q=book"})
        self.assertRedirects(response, "/words/?q=book", fetch_redirect_response=False)

    def test_ajax_behavior_does_not_redirect(self):
        response = self.client.post(
            self.url, {"next": "https://outside.example/steal"},
            HTTP_X_REQUESTED_WITH="fetch",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("color", response.json())


class JsonPayloadRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", verbosity=0)
        cls.exercise_id = Exercise.objects.filter(lesson__is_published=True).values_list("pk", flat=True).first()
        cls.unit_uid = LexicalUnit.objects.values_list("uid", flat=True).first()
        cls.poem_number = Poem.objects.filter(is_published=True).values_list("number", flat=True).first()
        assert cls.exercise_id is not None
        assert cls.unit_uid is not None
        assert cls.poem_number is not None

    def test_non_object_json_returns_400_for_all_exercise_endpoints(self):
        urls = (
            reverse("api:check_exercise", args=[self.exercise_id]),
            reverse("api:recall_unit", args=[self.unit_uid]),
            reverse("api:check_poem_gap", args=[self.poem_number, 0]),
        )
        for url in urls:
            for payload in ("[]", "null", '"answer"', "123", "true"):
                with self.subTest(url=url, payload=payload):
                    response = self.client.post(url, data=payload, content_type="application/json")
                    self.assertEqual(response.status_code, 400)

    def test_malformed_json_and_invalid_utf8_return_400(self):
        for url in (
            reverse("api:check_exercise", args=[self.exercise_id]),
            reverse("api:recall_unit", args=[self.unit_uid]),
            reverse("api:check_poem_gap", args=[self.poem_number, 0]),
        ):
            for payload in ("{bad", b"\xff"):
                with self.subTest(url=url, payload=payload):
                    response = self.client.post(url, data=payload, content_type="application/json")
                    self.assertEqual(response.status_code, 400)


class LinguisticMarkupRegressionTests(SimpleTestCase):
    def test_unclosed_opening_marker_is_reported(self):
        for text in ("Start [S1]book end", "[S1]cat[/] plain [D1]run", "[S1-#d32f2f]book"):
            with self.subTest(text=text):
                issues = find_issues(text)
                self.assertTrue(any("без закрывающего" in i.problem for i in issues), issues)

    def test_nested_markers_are_reported_instead_of_silently_swallowed(self):
        issues = find_issues("[S1]hello [D1]walk[/]")
        self.assertTrue(issues)

    def test_correct_markers_pass_unchanged(self):
        self.assertEqual(find_issues("[T3]My[/] [S1-#d32f2f]friend[/] [D1]is[/] here."), [])

    def test_stray_closing_marker_still_fails(self):
        self.assertTrue(find_issues("book[/]"))
