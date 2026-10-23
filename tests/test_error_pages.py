"""Public error pages remain useful even when application dependencies fail."""
from unittest.mock import patch

from django.http import Http404
from django.test import Client, RequestFactory, SimpleTestCase, override_settings
from django.urls import path
from django.views.defaults import server_error


def missing_page(request):
    raise Http404("private-missing-record-detail")


def broken_page(request):
    raise RuntimeError("private-server-failure-detail")


urlpatterns = [
    path("missing/", missing_page),
    path("broken/", broken_page),
]


@override_settings(DEBUG=False, ROOT_URLCONF=__name__)
class ErrorPageTests(SimpleTestCase):
    def test_missing_page_has_site_identity_and_safe_navigation(self):
        response = self.client.get("/missing/")
        self.assertContains(response, "Страница не найдена", status_code=404)
        self.assertContains(response, "English Encyclopedia", status_code=404)
        self.assertContains(response, 'href="/"', status_code=404)
        self.assertNotContains(response, "private-missing-record-detail", status_code=404)
        self.assertNotContains(response, "Http404", status_code=404)

    def test_unmatched_url_uses_the_same_custom_404(self):
        response = self.client.get("/does-not-exist/")
        self.assertContains(response, "Страница не найдена", status_code=404)

    def test_server_error_does_not_disclose_exception_or_framework_details(self):
        response = Client(raise_request_exception=False).get("/broken/")
        self.assertContains(response, "Не удалось открыть страницу", status_code=500)
        self.assertContains(response, "English Encyclopedia", status_code=500)
        self.assertContains(response, 'href="/"', status_code=500)
        for detail in ("private-server-failure-detail", "RuntimeError", "Traceback", "Django Version"):
            self.assertNotContains(response, detail, status_code=500)

    def test_server_error_renders_without_database_url_resolver_or_request_context(self):
        # SimpleTestCase rejects any database query. Rendering must also work
        # while the usual URL and site-context dependencies are unavailable.
        request = RequestFactory().get("/broken/")
        with (
            patch("django.urls.reverse", side_effect=AssertionError("URL resolver unavailable")),
            patch("apps.core.context_processors.site", side_effect=AssertionError("Site context unavailable")),
            patch("django.contrib.staticfiles.storage.staticfiles_storage.url", side_effect=AssertionError("Static manifest unavailable")),
        ):
            response = server_error(request)
        self.assertContains(response, "Не удалось открыть страницу", status_code=500)
        self.assertContains(response, '/static/css/studio.css', status_code=500)
