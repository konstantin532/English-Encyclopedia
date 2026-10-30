"""Роль из формы — намерение; права учителя выдаёт только владелец."""
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Permission
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.accounts.admin import EmailUserAdmin
from apps.accounts.models import User
from apps.teaching.access import can_teach


class SignupRoleTests(TestCase):
    def signup(self, **extra):
        return self.client.post(reverse("accounts:signup"), {
            "email": "new-role@example.test", "password1": "Local-long-pass-482!",
            "password2": "Local-long-pass-482!", **extra,
        })

    def test_student_default_and_injected_privileges(self):
        response = self.signup(is_teacher="on", teacher_sees_all="on", is_staff="on", is_superuser="on",
                               teacher_access_requested="on")
        self.assertRedirects(response, reverse("learning:dashboard"), fetch_redirect_response=False)
        user = User.objects.get(email="new-role@example.test")
        self.assertEqual((user.is_teacher, user.teacher_sees_all, user.is_staff, user.is_superuser,
                          user.teacher_access_requested), (False,) * 5)
        self.assertTrue(user.check_password("Local-long-pass-482!"))

    def test_teacher_choice_creates_request_and_never_grants_access(self):
        response = self.signup(role="teacher", is_teacher="on", teacher_sees_all="on")
        self.assertRedirects(response, reverse("accounts:teacher_request"))
        user = User.objects.get(email="new-role@example.test")
        self.assertTrue(user.teacher_access_requested)
        self.assertTrue(user.is_learner)  # ordinary learner rights until owner approval
        self.assertFalse(can_teach(user))
        self.assertFalse(user.teacher_sees_all)
        self.assertEqual(self.client.get(reverse("teaching:dashboard")).status_code, 403)

    def test_unknown_role_keeps_form_and_creates_nothing(self):
        response = self.signup(role="owner")
        self.assertEqual(response.status_code, 200)
        self.assertIn("role", response.context["form"].errors)
        self.assertFalse(User.objects.filter(email="new-role@example.test").exists())

    def test_pending_login_and_authenticated_signup_use_role_landing(self):
        user = User.objects.create_user("pending@example.test", "Local-long-pass-482!",
                                        teacher_access_requested=True)
        response = self.client.post(reverse("accounts:login"), {
            "username": user.email, "password": "Local-long-pass-482!"})
        self.assertRedirects(response, reverse("accounts:teacher_request"))
        self.assertRedirects(self.client.get(reverse("accounts:signup")), reverse("accounts:teacher_request"))

    def test_only_owner_can_decide_request_and_approval_then_revocation_routes_correctly(self):
        pending = User.objects.create_user("pending@example.test", teacher_access_requested=True)
        editor = User.objects.create_user("editor@example.test", is_staff=True)
        owner = User.objects.create_superuser("owner@example.test")
        model_admin = EmailUserAdmin(User, AdminSite())
        request = RequestFactory().post("/")
        request.user = editor
        self.assertIn("teacher_access_requested", model_admin.get_readonly_fields(request, pending))
        request.user = owner
        self.assertNotIn("teacher_access_requested", model_admin.get_readonly_fields(request, pending))
        pending.is_teacher = True
        model_admin.save_model(request, pending, None, True)
        pending.refresh_from_db()
        self.assertTrue(can_teach(pending))
        self.assertFalse(pending.teacher_access_requested)
        self.client.force_login(pending)
        self.assertRedirects(self.client.get(reverse("accounts:teacher_request")), reverse("teaching:dashboard"))
        pending.is_teacher = False
        model_admin.save_model(request, pending, None, True)
        self.assertRedirects(self.client.get(reverse("accounts:signup")), reverse("learning:dashboard"))

    @override_settings(EE_COURSE_LOGIN_REQUIRED=False)
    def test_request_status_itself_requires_login_even_without_course_wall(self):
        self.assertRedirects(self.client.get(reverse("accounts:teacher_request")),
                             reverse("accounts:login") + "?next=" + reverse("accounts:teacher_request"))

    def test_next_is_preserved_between_forms_and_used_for_student_signup(self):
        response = self.client.get(reverse("accounts:login"), {"next": "/learning/review/"})
        self.assertContains(response, 'href="/accounts/signup/?next=/learning/review/"')
        response = self.signup(role="student", next="/learning/review/")
        self.assertRedirects(response, "/learning/review/", fetch_redirect_response=False)

    def test_unsafe_next_and_auth_loops_are_ignored(self):
        for index, destination in enumerate(("https://evil.example/", "//evil.example/", "/accounts/login/?x=1",
                                              "/accounts/signup/", "http://[bad")):
            with self.subTest(destination=destination):
                self.client.logout()
                response = self.signup(email=f"next-{index}@example.test", next=destination)
                self.assertRedirects(response, reverse("learning:dashboard"), fetch_redirect_response=False)

    def test_signup_csrf_still_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("accounts:signup"), {"role": "teacher"}).status_code, 403)

    def test_admin_http_staff_cannot_forge_approval_or_dismiss_request(self):
        pending = User.objects.create_user("pending@example.test", teacher_access_requested=True)
        editor = User.objects.create_user("editor@example.test", is_staff=True)
        editor.user_permissions.add(Permission.objects.get(codename="change_user", content_type__app_label="accounts"))
        self.client.force_login(editor)
        response = self.client.post(reverse("admin:accounts_user_change", args=[pending.pk]), {
            "email": pending.email, "is_active": "on", "is_teacher": "on", "teacher_sees_all": "on",
            "is_staff": "on", "is_superuser": "on", "teacher_access_requested": "", "_save": "Сохранить",
        })
        self.assertEqual(response.status_code, 302)
        pending.refresh_from_db()
        self.assertTrue(pending.teacher_access_requested)
        self.assertEqual((pending.is_teacher, pending.teacher_sees_all, pending.is_staff, pending.is_superuser), (False,) * 4)

    def test_admin_http_owner_approves_request(self):
        pending = User.objects.create_user("pending@example.test", teacher_access_requested=True)
        owner = User.objects.create_superuser("owner@example.test")
        self.client.force_login(owner)
        response = self.client.post(reverse("admin:accounts_user_change", args=[pending.pk]), {
            "email": pending.email, "is_active": "on", "is_teacher": "on", "teacher_access_requested": "on",
            "_save": "Сохранить",
        })
        self.assertEqual(response.status_code, 302)
        pending.refresh_from_db()
        self.assertTrue(can_teach(pending))
        self.assertFalse(pending.teacher_access_requested)
        self.assertFalse(pending.teacher_sees_all)


class GuestShellTests(TestCase):
    def test_guest_home_opens_separate_login(self):
        self.assertRedirects(self.client.get("/"), reverse("accounts:login"))

    def test_public_forms_hide_learning_interface_and_omit_name(self):
        for route in ("accounts:login", "accounts:signup"):
            response = self.client.get(reverse(route))
            self.assertContains(response, 'data-public-shell')
            self.assertNotContains(response, 'class="studio-sidebar')
            self.assertNotContains(response, 'role="search"')
            self.assertNotContains(response, 'data-motion-control')
            self.assertNotContains(response, 'data-markers-toggle')
        response = self.client.get(reverse("accounts:signup"))
        self.assertContains(response, 'name="role"', count=2)
        self.assertContains(response, 'value="teacher"')
        self.assertNotContains(response, 'name="display_name"')
        self.assertContains(response, 'name="password2"')

    def test_logged_in_student_keeps_learning_navigation(self):
        user = User.objects.create_user("student-shell@example.test")
        self.client.force_login(user)
        response = self.client.get("/")
        self.assertContains(response, 'class="studio-sidebar atlas-sidebar"')
        self.assertContains(response, 'role="search"')
