"""Черновики уроков и историй от учителей: только свои, на сайт сами не попадают."""
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.teaching.admin import ContentDraftAdmin
from apps.teaching.models import ContentDraft

DRAFT = {"kind": "lesson", "level": "A1+", "week": "3", "title": "Small talk at work",
         "body": "Как ответить коллеге «Not bad!» — и почему не «Normal»."}


class TeacherDraftTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user("t@example.com", "pass-12345", is_teacher=True)
        cls.other = User.objects.create_user("o@example.com", "pass-12345", is_teacher=True)
        cls.learner = User.objects.create_user("l@example.com", "pass-12345")
        cls.owner = User.objects.create_superuser("own@example.com", "pass-12345")
        cls.foreign = ContentDraft.objects.create(author=cls.other, title="Theirs", body="x")

    def test_teacher_saves_and_submits(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse("teaching:draft_new"), {**DRAFT, "save": "1"})
        draft = ContentDraft.objects.get(author=self.teacher)
        self.assertEqual(draft.status, "draft")
        self.client.post(reverse("teaching:draft_edit", args=[draft.pk]), {**DRAFT, "submit": "1"})
        draft.refresh_from_db()
        self.assertEqual(draft.status, "submitted")
        self.assertIsNotNone(draft.submitted_at)

    def test_submitted_draft_is_locked(self):
        self.client.force_login(self.teacher)
        draft = ContentDraft.objects.create(author=self.teacher, title="Locked", body="b", status="submitted")
        self.client.post(reverse("teaching:draft_edit", args=[draft.pk]), {**DRAFT, "title": "Changed", "save": "1"})
        self.client.post(reverse("teaching:draft_delete", args=[draft.pk]))
        draft.refresh_from_db()
        self.assertEqual((draft.title, draft.status), ("Locked", "submitted"))

    def test_rejected_draft_can_be_reworked(self):
        self.client.force_login(self.teacher)
        draft = ContentDraft.objects.create(author=self.teacher, title="Again", body="b", status="rejected")
        self.client.post(reverse("teaching:draft_edit", args=[draft.pk]), {**DRAFT, "submit": "1"})
        draft.refresh_from_db()
        self.assertEqual(draft.status, "submitted")

    def test_foreign_drafts_are_invisible(self):
        self.client.force_login(self.teacher)
        self.assertNotIn("Theirs", self.client.get(reverse("teaching:drafts")).content.decode())
        self.assertEqual(self.client.get(reverse("teaching:draft_edit", args=[self.foreign.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("teaching:draft_delete", args=[self.foreign.pk])).status_code, 404)
        self.assertTrue(ContentDraft.objects.filter(pk=self.foreign.pk).exists())

    def test_teacher_cannot_approve_own_draft(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse("teaching:draft_new"), {**DRAFT, "status": "approved", "owner_note": "ok", "submit": "1"})
        draft = ContentDraft.objects.get(author=self.teacher)
        self.assertEqual((draft.status, draft.owner_note), ("submitted", ""))

    def test_learner_has_no_drafts(self):
        self.client.force_login(self.learner)
        self.assertEqual(self.client.get(reverse("teaching:drafts")).status_code, 403)
        self.assertEqual(self.client.post(reverse("teaching:draft_new"), DRAFT).status_code, 403)

    def test_bad_week_rejected(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse("teaching:draft_new"), {**DRAFT, "week": "99"})
        self.assertFalse(ContentDraft.objects.filter(author=self.teacher).exists())

    def test_draft_never_becomes_a_published_lesson_by_itself(self):
        from apps.lessons.models import Lesson
        from apps.stories.models import Story
        before = (Lesson.objects.count(), Story.objects.count())
        self.client.force_login(self.teacher)
        self.client.post(reverse("teaching:draft_new"), {**DRAFT, "submit": "1"})
        ContentDraft.objects.filter(author=self.teacher).update(status="approved")
        self.assertEqual((Lesson.objects.count(), Story.objects.count()), before)

    def test_owner_downloads_markdown(self):
        admin = ContentDraftAdmin(ContentDraft, AdminSite())
        request = RequestFactory().get("/")
        request.user = self.owner
        response = admin.download_markdown(request, ContentDraft.objects.filter(pk=self.foreign.pk))
        self.assertIn("# Theirs", response.content.decode())
        self.assertIn("attachment", response["Content-Disposition"])

    def test_teacher_without_groups_can_delete_account_drafts_stay(self):
        lone = User.objects.create_user("lone@example.com", "pass-12345", is_teacher=True)
        draft = ContentDraft.objects.create(author=lone, title="Kept for owner", body="b", status="submitted")
        self.client.force_login(lone)
        self.client.post(reverse("accounts:delete_account"), {"confirm": "УДАЛИТЬ", "password": "pass-12345"})
        self.assertFalse(User.objects.filter(pk=lone.pk).exists())
        draft.refresh_from_db()
        self.assertIsNone(draft.author)
