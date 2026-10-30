from django.test import TestCase, override_settings
from django.urls import reverse
from tests.runner import ensure_content


class PublicMetadataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    @override_settings(PUBLIC_SITE_URL="https://english.example")
    def test_public_canonical_ignores_query_and_request_host(self):
        response = self.client.get("/for-teachers/?campaign=test")
        self.assertContains(response, 'rel="canonical" href="https://english.example/for-teachers/"')
        self.assertContains(
            response, 'property="og:url" content="https://english.example/for-teachers/"'
        )
        self.assertNotContains(response, "campaign=test")

    @override_settings(PUBLIC_SITE_URL="https://english.example")
    def test_login_is_not_a_public_search_landing_page(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, 'content="noindex, follow"')
        self.assertNotContains(response, 'rel="canonical"')

    @override_settings(PUBLIC_SITE_URL="")
    def test_unconfigured_origin_does_not_invent_canonical(self):
        self.assertNotContains(self.client.get("/for-teachers/"), 'rel="canonical"')

    @override_settings(PUBLIC_SITE_URL="https://english.example")
    def test_robots_excludes_private_routes_and_links_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Disallow: /learning/", response.content)
        self.assertIn(b"Sitemap: https://english.example/sitemap.xml", response.content)

    @override_settings(PUBLIC_SITE_URL="https://english.example")
    def test_sitemap_contains_only_published_public_material(self):
        from apps.lessons.models import Lesson

        lesson = Lesson.objects.first()
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            (
                "https://english.example"
                + reverse("lessons:detail", args=[lesson.slug])
            ).encode(),
            response.content,
        )
        self.assertNotIn(b"/learning/", response.content)
        lesson.is_published = False
        lesson.save()
        self.assertNotIn(
            reverse("lessons:detail", args=[lesson.slug]).encode(),
            self.client.get("/sitemap.xml").content,
        )

    @override_settings(PUBLIC_SITE_URL="https://user:password@example.com")
    def test_origin_with_credentials_is_not_published(self):
        self.assertNotContains(self.client.get("/for-teachers/"), 'rel="canonical"')
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 404)

    def test_logged_in_home_links_to_existing_learning_dashboard(self):
        from apps.accounts.models import User

        user = User.objects.create_user(
            email="design-reader@example.test", password="test-only-password"
        )
        self.client.force_login(user)
        response = self.client.get("/")
        self.assertContains(response, "Продолжить обучение")
        self.assertContains(response, 'href="' + reverse("learning:dashboard") + '"')
