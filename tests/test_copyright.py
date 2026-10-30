from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


class CopyrightTests(TestCase):
    def test_license_reserves_rights(self):
        text = (Path(settings.BASE_DIR) / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Все права защищены", text)
        self.assertIn("All rights reserved", text)
        self.assertIn("SIL Open Font License", text)

    def test_footer_shows_copyright(self):
        response = self.client.get(reverse("core:home"), follow=True)
        self.assertContains(response, "© 2026 konstantin532. Все права защищены.")
