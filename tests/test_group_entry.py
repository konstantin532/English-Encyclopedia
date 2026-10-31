"""Group entry must be easy to find and agree with the account's permissions."""
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.admin import EmailUserAdmin
from apps.accounts.models import User
from apps.teaching.models import GroupMembership, StudyGroup


class GroupEntryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user('group-student@example.test')
        cls.pending = User.objects.create_user('group-pending@example.test', teacher_access_requested=True)
        cls.teacher = User.objects.create_user('group-teacher@example.test', is_teacher=True)
        cls.staff = User.objects.create_user('group-staff@example.test', is_staff=True)
        cls.owner = User.objects.create_superuser('group-owner@example.test', 'fixture-password')
        cls.group = StudyGroup.objects.create(teacher=cls.teacher, name='Unlisted fixture group')

    def test_student_can_find_group_in_main_navigation(self):
        self.client.force_login(self.student)
        page = self.client.get(reverse('learning:dashboard'))
        self.assertContains(page, 'data-group-nav', count=1)
        self.assertContains(page, 'class="btn btn-quiet" href="/group/"')
        group_page = self.client.get(reverse('teaching:join'))
        self.assertContains(group_page, 'data-group-nav aria-current="page"')
        self.assertContains(group_page, 'name="code"')
        self.assertContains(group_page, 'Группы не публикуются в общем каталоге.')

    def test_nonlearners_see_role_explanation_instead_of_join_form(self):
        for user, label in ((self.staff, 'служебного аккаунта'),
                            (self.teacher, 'аккаунта учителя'), (self.owner, 'аккаунта владельца')):
            with self.subTest(role=label):
                self.client.force_login(user)
                page = self.client.get(reverse('teaching:join'))
                self.assertContains(page, 'data-group-ineligible')
                self.assertContains(page, label)
                self.assertNotContains(page, 'name="code"')
                self.assertNotContains(page, 'data-group-nav')
                self.assertContains(page, 'Войти как ученик')
                progress = self.client.get(reverse('learning:dashboard'))
                self.assertNotContains(progress, 'data-group-link')

    def test_nonlearner_post_is_rejected_without_membership_or_group_disclosure(self):
        for user in (self.staff, self.teacher, self.owner):
            with self.subTest(user=user.pk):
                self.client.force_login(user)
                response = self.client.post(reverse('teaching:join'), {'code': self.group.join_code})
                self.assertEqual(response.status_code, 403)
                self.assertContains(response, 'data-group-ineligible', status_code=403)
                self.assertNotContains(response, self.group.name, status_code=403)
                self.assertFalse(GroupMembership.objects.filter(student=user).exists())

    def test_pending_teacher_still_joins_as_learner(self):
        self.client.force_login(self.pending)
        self.assertContains(self.client.get(reverse('teaching:join')), 'name="code"')
        response = self.client.post(reverse('teaching:join'), {'code': self.group.join_code})
        self.assertRedirects(response, reverse('teaching:join'))
        self.assertEqual(GroupMembership.objects.get(student=self.pending).group_id, self.group.pk)

    def test_guest_still_needs_login(self):
        response = self.client.get(reverse('teaching:join'))
        self.assertRedirects(response, '/accounts/login/?next=/group/', fetch_redirect_response=False)

    def test_role_switch_logs_out_before_offering_student_login(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('accounts:logout'), {'next': '/accounts/login/?next=/group/'})
        self.assertRedirects(response, '/accounts/login/?next=/group/')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_clearing_staff_flag_restores_student_entry_without_affecting_teacher(self):
        self.staff.is_staff = False
        self.staff.save(update_fields=['is_staff'])
        self.client.force_login(self.staff)
        response = self.client.post(reverse('teaching:join'), {'code': self.group.join_code})
        self.assertRedirects(response, reverse('teaching:join'))
        self.assertEqual(GroupMembership.objects.get(student=self.staff).group_id, self.group.pk)
        self.teacher.refresh_from_db()
        self.owner.refresh_from_db()
        self.assertTrue(self.teacher.is_teacher)
        self.assertTrue(self.owner.is_superuser)

    def test_admin_explains_staff_flag_in_group_terms(self):
        request = RequestFactory().get('/')
        request.user = self.owner
        form = EmailUserAdmin(User, AdminSite()).get_form(request, self.student)
        self.assertEqual(form.base_fields['is_staff'].label, 'Служебный доступ в админку')
        self.assertIn('не сможет вступать в группы как ученик', form.base_fields['is_staff'].help_text)
