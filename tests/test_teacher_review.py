"""Проверка свободных ответов учителем и сообщения об ошибках курса."""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.learning.models import IndependentAttempt
from apps.lessons.models import Lesson
from apps.teaching.models import CourseIssue, GroupMembership, StudyGroup
from apps.teaching.views import ISSUES_PER_DAY
from tests.runner import ensure_content

GOOD_NOTE = "Смысл передан, форма верная: отличный вопрос с did."


class TeacherReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        mk = User.objects.create_user
        cls.teacher = mk("t@example.com", "pass-12345", is_teacher=True)
        cls.other_teacher = mk("t2@example.com", "pass-12345", is_teacher=True)
        cls.mine = mk("mine@example.com", "pass-12345")
        cls.foreign = mk("foreign@example.com", "pass-12345")
        GroupMembership.objects.create(group=StudyGroup.objects.create(teacher=cls.teacher, name="G"), student=cls.mine)
        GroupMembership.objects.create(group=StudyGroup.objects.create(teacher=cls.other_teacher, name="H"),
                                       student=cls.foreign)
        lesson = Lesson.objects.filter(level__code="A1").first()

        def attempt(user, outcome=IndependentAttempt.Outcome.NEEDS_REVIEW):
            return IndependentAttempt.objects.create(
                user=user, lesson=lesson, skill="transfer", submitted="Did you take bus twelve?",
                prompt_snapshot="Спросите, на каком автобусе ехал друг.", model_snapshot="Which bus did you take?",
                outcome=outcome)
        cls.my_attempt = attempt(cls.mine)
        cls.foreign_attempt = attempt(cls.foreign)
        cls.machine_checked = attempt(cls.mine, IndependentAttempt.Outcome.MODEL_MATCH)

    def post_review(self, attempt, **data):
        payload = {"teacher_verdict": "meets_task", "rubric_meaning": "yes", "rubric_form": "yes",
                   "rubric_context": "yes", "teacher_note": GOOD_NOTE}
        payload.update(data)
        return self.client.post(reverse("teaching:review", args=[attempt.pk]), payload)

    def test_queue_has_only_own_students_unreviewed_free_answers(self):
        self.client.force_login(self.teacher)
        queue = list(self.client.get(reverse("teaching:review_list")).context["queue"])
        self.assertEqual(queue, [self.my_attempt])

    def test_foreign_answer_is_invisible(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(reverse("teaching:review", args=[self.foreign_attempt.pk])).status_code, 404)
        self.assertEqual(self.post_review(self.foreign_attempt).status_code, 404)
        self.foreign_attempt.refresh_from_db()
        self.assertEqual(self.foreign_attempt.teacher_verdict, "unreviewed")

    def test_valid_review_is_saved_with_reviewer(self):
        self.client.force_login(self.teacher)
        self.post_review(self.my_attempt)
        self.my_attempt.refresh_from_db()
        self.assertEqual(self.my_attempt.teacher_verdict, "meets_task")
        self.assertEqual(self.my_attempt.reviewed_by, self.teacher)
        self.assertEqual(self.my_attempt.teacher_rubric, {"meaning": "yes", "form": "yes", "context": "yes"})
        self.assertIsNotNone(self.my_attempt.reviewed_at)

    def test_review_rules_match_admin(self):
        self.client.force_login(self.teacher)
        for bad in ({"rubric_form": "partly"}, {"teacher_note": "ок"}, {"rubric_context": ""}):
            with self.subTest(bad=bad):
                self.post_review(self.my_attempt, **bad)
                self.my_attempt.refresh_from_db()
                self.assertEqual(self.my_attempt.teacher_verdict, "unreviewed")

    def test_teacher_cannot_change_the_answer_itself(self):
        self.client.force_login(self.teacher)
        self.post_review(self.my_attempt, submitted="hacked", outcome="model_match", user=self.foreign.pk)
        self.my_attempt.refresh_from_db()
        self.assertEqual(self.my_attempt.submitted, "Did you take bus twelve?")
        self.assertEqual(self.my_attempt.user, self.mine)

    def test_learner_cannot_review(self):
        self.client.force_login(self.mine)
        self.assertEqual(self.client.get(reverse("teaching:review_list")).status_code, 403)
        self.assertEqual(self.post_review(self.my_attempt).status_code, 403)


class CourseIssueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = User.objects.create_user("l@example.com", "pass-12345")
        cls.teacher = User.objects.create_user("t@example.com", "pass-12345", is_teacher=True)

    def report(self, page="/levels/a1/weeks/2/", **extra):
        data = {"page": page, "quote": "I am well.", "comment": "Так американцы не говорят."}
        data.update(extra)
        return self.client.post(reverse("teaching:report_issue"), data)

    def test_learner_reports_and_returns_to_page(self):
        self.client.force_login(self.learner)
        response = self.report()
        self.assertEqual(response["Location"], reverse("teaching:report_issue") + "?sent=1&page=/levels/a1/weeks/2/")
        page = self.client.get(response["Location"]).content.decode()
        self.assertIn("Вернуться к странице", page)
        issue = CourseIssue.objects.get()
        self.assertEqual((issue.reporter, issue.reporter_is_teacher, issue.status), (self.learner, False, "open"))

    def test_teacher_report_is_marked(self):
        self.client.force_login(self.teacher)
        self.report()
        self.assertTrue(CourseIssue.objects.get().reporter_is_teacher)

    def test_foreign_or_odd_pages_are_rejected(self):
        self.client.force_login(self.learner)
        for page in ("//evil.example/x", "https://evil.example/", "javascript:alert(1)", ""):
            with self.subTest(page=page):
                self.report(page=page)
        self.assertFalse(CourseIssue.objects.exists())

    def test_daily_limit(self):
        self.client.force_login(self.learner)
        for _ in range(ISSUES_PER_DAY + 3):
            self.report()
        self.assertEqual(CourseIssue.objects.count(), ISSUES_PER_DAY)

    def test_anonymous_cannot_report(self):
        response = self.report()
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
        self.assertFalse(CourseIssue.objects.exists())
