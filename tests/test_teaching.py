"""Роль учителя, группы и права: кто кого видит."""
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.admin import EmailUserAdmin
from apps.accounts.models import User
from apps.teaching.access import visible_students
from apps.teaching.models import CODE_ALPHABET, GroupMembership, StudyGroup


class TeachingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        mk = User.objects.create_user
        cls.owner = User.objects.create_superuser("owner@example.com", "pass-12345")
        cls.teacher_a = mk("a@example.com", "pass-12345", is_teacher=True, display_name="Teacher A")
        cls.teacher_b = mk("b@example.com", "pass-12345", is_teacher=True)
        cls.teacher_all = mk("all@example.com", "pass-12345", is_teacher=True, teacher_sees_all=True)
        cls.editor = mk("editor@example.com", "pass-12345", is_staff=True)
        cls.student_a = mk("sa@example.com", "pass-12345", display_name="Student A")
        cls.student_b = mk("sb@example.com", "pass-12345", display_name="Student B")
        cls.loner = mk("loner@example.com", "pass-12345")
        cls.group_a = StudyGroup.objects.create(teacher=cls.teacher_a, name="A")
        cls.group_b = StudyGroup.objects.create(teacher=cls.teacher_b, name="B")
        GroupMembership.objects.create(group=cls.group_a, student=cls.student_a)
        GroupMembership.objects.create(group=cls.group_b, student=cls.student_b)

    # --- кто кого видит -------------------------------------------------------
    def test_teacher_sees_only_own_group(self):
        self.assertEqual(list(visible_students(self.teacher_a)), [self.student_a])
        self.assertEqual(list(visible_students(self.teacher_b)), [self.student_b])

    def test_teacher_with_all_access_and_owner_see_every_learner(self):
        everyone = {self.student_a, self.student_b, self.loner}
        self.assertEqual(set(visible_students(self.teacher_all)), everyone)
        self.assertEqual(set(visible_students(self.owner)), everyone)

    def test_learners_and_team_see_nobody(self):
        for user in (self.student_a, self.loner, self.editor):
            with self.subTest(user=user):
                self.assertFalse(visible_students(user).exists())

    def test_teachers_and_team_are_never_listed_as_students(self):
        listed = set(visible_students(self.owner))
        self.assertFalse(listed & {self.teacher_a, self.teacher_b, self.teacher_all, self.editor, self.owner})

    def test_student_list_and_detail_respect_groups(self):
        self.client.force_login(self.teacher_a)
        page = self.client.get(reverse("teaching:students")).content.decode()
        self.assertIn("Student A", page)
        self.assertNotIn("Student B", page)
        self.assertEqual(self.client.get(reverse("teaching:student", args=[self.student_a.pk])).status_code, 200)
        # Чужой ученик — 404: учитель не узнаёт даже о его существовании.
        self.assertEqual(self.client.get(reverse("teaching:student", args=[self.student_b.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("teaching:student", args=[self.teacher_b.pk])).status_code, 404)

    def test_cabinet_is_closed_to_learners_and_team(self):
        for user in (self.student_a, self.editor):
            self.client.force_login(user)
            for name in ("teaching:dashboard", "teaching:students"):
                with self.subTest(user=user, name=name):
                    self.assertEqual(self.client.get(reverse(name)).status_code, 403)
            self.assertEqual(self.client.get(reverse("teaching:student", args=[self.student_a.pk])).status_code, 403)

    def test_inactive_teacher_loses_access(self):
        self.teacher_a.is_active = False
        self.teacher_a.save()
        self.assertFalse(visible_students(self.teacher_a).exists())

    # --- группы -----------------------------------------------------------
    def test_teacher_creates_group_with_readable_code(self):
        self.client.force_login(self.teacher_a)
        self.client.post(reverse("teaching:dashboard"), {"name": "Evening"})
        group = StudyGroup.objects.get(name="Evening")
        self.assertEqual(group.teacher, self.teacher_a)
        self.assertEqual(len(group.join_code), 8)
        self.assertTrue(set(group.join_code) <= set(CODE_ALPHABET))
        self.assertFalse(set(group.join_code) & set("0O1IL"))

    def test_learner_cannot_create_group(self):
        self.client.force_login(self.loner)
        self.assertEqual(self.client.post(reverse("teaching:dashboard"), {"name": "X"}).status_code, 403)
        self.assertFalse(StudyGroup.objects.filter(name="X").exists())

    def test_learner_joins_by_code_typed_loosely(self):
        self.client.force_login(self.loner)
        code = self.group_a.join_code
        loose = f" {code[:4].lower()}-{code[4:]} "
        self.client.post(reverse("teaching:join"), {"code": loose})
        self.assertEqual(GroupMembership.objects.get(student=self.loner).group, self.group_a)
        self.assertIn(self.loner, visible_students(self.teacher_a))
        self.assertNotIn(self.loner, visible_students(self.teacher_b))

    def test_switching_group_moves_student(self):
        self.client.force_login(self.student_a)
        self.client.post(reverse("teaching:join"), {"code": self.group_b.join_code})
        self.assertNotIn(self.student_a, visible_students(self.teacher_a))
        self.assertIn(self.student_a, visible_students(self.teacher_b))
        self.assertEqual(GroupMembership.objects.filter(student=self.student_a).count(), 1)

    def test_closed_or_unknown_group_rejected(self):
        self.group_b.is_open = False
        self.group_b.save()
        self.client.force_login(self.loner)
        for code in (self.group_b.join_code, "ZZZZZZZZ"):
            with self.subTest(code=code):
                self.client.post(reverse("teaching:join"), {"code": code})
                self.assertFalse(GroupMembership.objects.filter(student=self.loner).exists())

    def test_teacher_cannot_join_a_group_as_student(self):
        self.client.force_login(self.teacher_b)
        self.client.post(reverse("teaching:join"), {"code": self.group_a.join_code})
        self.assertFalse(GroupMembership.objects.filter(student=self.teacher_b).exists())

    def test_leave_group(self):
        self.client.force_login(self.student_a)
        self.client.post(reverse("teaching:leave"))
        self.assertNotIn(self.student_a, visible_students(self.teacher_a))

    # --- вход и роли ------------------------------------------------------
    def test_teacher_lands_in_cabinet_learner_in_course(self):
        teacher = self.client.post(reverse("accounts:login"), {"username": "a@example.com", "password": "pass-12345"})
        self.assertEqual(teacher["Location"], reverse("teaching:dashboard"))
        self.client.logout()
        learner = self.client.post(reverse("accounts:login"), {"username": "sa@example.com", "password": "pass-12345"})
        self.assertEqual(learner["Location"], reverse("learning:dashboard"))

    def test_only_owner_can_assign_teacher_role_in_admin(self):
        admin = EmailUserAdmin(User, AdminSite())
        request = RequestFactory().get("/")
        request.user = self.editor
        self.assertIn("is_teacher", admin.get_readonly_fields(request, self.loner))
        self.assertIn("teacher_sees_all", admin.get_readonly_fields(request, self.loner))
        request.user = self.owner
        self.assertNotIn("is_teacher", admin.get_readonly_fields(request, self.loner))

    def test_signup_never_creates_a_teacher(self):
        self.client.post(reverse("accounts:signup"), {
            "email": "new@example.com", "password1": "Long-pass-9876", "password2": "Long-pass-9876",
            "is_teacher": "on", "teacher_sees_all": "on",
        })
        user = User.objects.get(email="new@example.com")
        self.assertFalse(user.is_teacher)
        self.assertFalse(user.teacher_sees_all)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)


class TeachingReviewFixesTests(TestCase):
    """Находки ревью PR #153–155: R4 (группа владельца), R5 (удаление учителя), R6 (запросы списка)."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_superuser("owner@example.com", "pass-12345")
        cls.teacher = User.objects.create_user("t@example.com", "pass-12345", is_teacher=True)

    def test_owner_without_teacher_flag_can_run_a_group_in_cabinet_and_admin(self):
        from apps.teaching.admin import StudyGroupAdmin
        self.client.force_login(self.owner)
        self.client.post(reverse("teaching:dashboard"), {"name": "Owner group"})
        group = StudyGroup.objects.get(name="Owner group")
        admin = StudyGroupAdmin(StudyGroup, AdminSite())
        request = RequestFactory().get("/")
        request.user = self.owner
        field = admin.formfield_for_foreignkey(StudyGroup._meta.get_field("teacher"), request)
        self.assertIn(group.teacher, field.queryset)

    def test_teacher_with_groups_gets_a_clear_refusal_and_stays_logged_in(self):
        StudyGroup.objects.create(teacher=self.teacher, name="Kept")
        self.client.force_login(self.teacher)
        response = self.client.post(reverse("accounts:delete_account"), {"confirm": "УДАЛИТЬ", "password": "pass-12345"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("группы учеников", response.content.decode())
        self.assertTrue(User.objects.filter(pk=self.teacher.pk).exists())
        self.assertEqual(self.client.get(reverse("teaching:dashboard")).status_code, 200)

    def test_student_list_query_count_does_not_grow_with_students(self):
        group = StudyGroup.objects.create(teacher=self.teacher, name="Big")
        self.client.force_login(self.teacher)

        def add(n):
            for i in range(n):
                s = User.objects.create_user(f"s{User.objects.count()}-{i}@example.com", "pass-12345")
                GroupMembership.objects.create(group=group, student=s)
        add(2)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as few:
            self.client.get(reverse("teaching:students"))
        add(20)
        with CaptureQueriesContext(connection) as many:
            response = self.client.get(reverse("teaching:students"))
        self.assertEqual(len(response.context["rows"]), 22)
        self.assertEqual(len(few), len(many))
