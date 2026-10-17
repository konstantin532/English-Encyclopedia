"""Studio rendering and model-permission boundaries."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from apps.core.templatetags.admin_studio import studio_metrics
from apps.lessons.models import Lesson
from django.test import RequestFactory


class AdminStudioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = get_user_model().objects.create_user(email="studio-test@example.com", password="test-only", is_staff=True)
        cls.owner = get_user_model().objects.create_superuser(email="studio-owner@example.com", password="test-only")

    def test_staff_without_model_permissions_sees_no_counts_or_sections(self):
        self.client.force_login(self.editor)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="studio-metric"')
        self.assertNotContains(response, reverse("admin:lexicon_lexicalunit_changelist"))

    def test_view_only_editor_sees_only_permitted_model_and_no_add_link(self):
        self.editor.user_permissions.add(Permission.objects.get(codename="view_lesson", content_type__app_label="lessons"))
        self.client.force_login(self.editor)
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, reverse("admin:lessons_lesson_changelist"))
        self.assertNotContains(response, reverse("admin:lessons_lesson_add"))
        self.assertNotContains(response, reverse("admin:accounts_user_changelist"))
        self.assertContains(response, 'class="studio-metric"', count=1)

    def test_owner_dashboard_renders_counts_and_standard_editor(self):
        request = RequestFactory().get("/admin/")
        request.user = self.owner
        cards = studio_metrics({"request": request})
        lesson_card = next(card for card in cards if card["title"] == "Уроков")
        self.assertEqual(lesson_card["count"], Lesson.objects.count())
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse("admin:index")), "Библиотека материалов")
        self.assertContains(self.client.get(reverse("admin:lessons_lesson_add")), "admin-studio.css")

    def test_anonymous_visitor_still_requires_login(self):
        response = self.client.get(reverse("admin:index"))
        self.assertRedirects(response, reverse("admin:login") + "?next=/admin/")
        self.assertContains(self.client.get(reverse("admin:login")), "admin-studio.css")


class AdminPeopleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_superuser(email="owner-people@example.com", password="test-only")
        cls.learner = User.objects.create_user(email="learner-people@example.com", display_name="<script>alert(1)</script>")
        cls.team = User.objects.create_user(email="team-people@example.com", is_staff=True, is_active=False)

    def setUp(self):
        self.client.force_login(self.owner)

    def test_people_summary_tracks_search_and_role_filters(self):
        response = self.client.get(reverse("admin:accounts_user_changelist"), {"role": "learners", "q": "learner-people"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["studio_user_stats"], {"total": 1, "active": 1, "team": 0})
        self.assertEqual(list(response.context["cl"].queryset), [self.learner])
        for tab in response.context["studio_role_tabs"]:
            self.assertIn("q=learner-people", tab["url"])

    def test_roles_do_not_overlap_and_disabled_staff_remains_visible(self):
        response = self.client.get(reverse("admin:accounts_user_changelist"), {"role": "editors"})
        self.assertEqual(list(response.context["cl"].queryset), [self.team])
        self.assertEqual(response.context["studio_user_stats"], {"total": 1, "active": 0, "team": 1})
        self.assertContains(response, "Отключён")
        admins = self.client.get(reverse("admin:accounts_user_changelist"), {"role": "admins"})
        self.assertEqual(list(admins.context["cl"].queryset), [self.owner])

    def test_display_name_is_escaped_inside_identity_markup(self):
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_view_only_staff_sees_table_without_add_button(self):
        self.team.is_active = True
        self.team.save(update_fields=["is_active"])
        self.team.user_permissions.add(Permission.objects.get(codename="view_user", content_type__app_label="accounts"))
        self.client.force_login(self.team)
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("admin:accounts_user_add"))

    def test_forms_keep_profile_fields_and_readonly_activity_dates(self):
        response = self.client.get(reverse("admin:accounts_user_change", args=[self.learner.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Профиль и обучение")
        self.assertContains(response, "Уровень английского")
        self.assertNotIn("last_login", response.context["adminform"].form.fields)
        self.assertEqual(self.client.get(reverse("admin:accounts_user_add")).status_code, 200)
