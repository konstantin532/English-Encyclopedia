"""Never grant a site-wide RLS policy to public Supabase Data API roles."""
import os
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.db_security import app_role, grant_app_role, enable_rls_on_public_tables


class RestrictedApplicationRoleTests(SimpleTestCase):
    def test_client_and_superuser_roles_cannot_be_selected(self):
        # These values match PostgreSQL syntax but must never receive a
        # global USING (true) policy over Django learner tables.
        for role in (
            "anon", "authenticated", "service_role", "postgres",
            "public", "supabase_admin", "pg_read_all_data", "website",
        ):
            with self.subTest(role=role), patch.dict(os.environ, {"APP_DB_ROLE": role}):
                with self.assertRaisesRegex(ValueError, "отдельная роль"):
                    app_role()

    def test_dedicated_role_remains_configurable(self):
        for role in ("ee_app", "ee_test_app", "ee_app_2"):
            with self.subTest(role=role), patch.dict(os.environ, {"APP_DB_ROLE": role}):
                self.assertEqual(app_role(), role)

    def test_direct_grant_rejects_public_role_without_running_sql(self):
        with patch("apps.core.db_security.connection") as database:
            database.vendor = "postgresql"
            with self.assertRaisesRegex(ValueError, "отдельная роль"):
                grant_app_role("anon")
            database.cursor.assert_not_called()

    def test_post_migrate_fails_closed_before_any_rls_sql(self):
        with patch.dict(os.environ, {"APP_DB_ROLE": "authenticated"}):
            with patch("apps.core.db_security.connection") as database:
                database.vendor = "postgresql"
                with self.assertRaisesRegex(ValueError, "отдельная роль"):
                    enable_rls_on_public_tables(sender=type("Accounts", (), {"label": "accounts"})())
                database.cursor.assert_not_called()
