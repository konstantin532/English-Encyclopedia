"""The RLS hook must be reached by Django's real post-migrate dispatcher."""
from unittest.mock import MagicMock, patch

from django.core.management.sql import emit_post_migrate_signal
from django.db.models.signals import Signal
from django.test import SimpleTestCase

from apps.core.db_security import enable_rls_on_public_tables


class RlsMigrationDispatchTests(SimpleTestCase):
    def test_migrate_dispatch_reaches_rls_protection(self):
        signal = Signal()
        signal.connect(enable_rls_on_public_tables)
        database = MagicMock(vendor="postgresql")
        cursor = database.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [("accounts_user",)]
        # Isolate other apps' handlers, but keep Django's real installed-app
        # discovery and dispatch: a direct receiver call hid this regression.
        with patch("django.db.models.signals.post_migrate", signal), patch(
            "apps.core.db_security.connection", database
        ), patch("apps.core.db_security.grant_app_role") as grant:
            emit_post_migrate_signal(verbosity=0, interactive=False, db="default")
        cursor.execute.assert_any_call(
            'alter table public."accounts_user" enable row level security'
        )
        grant.assert_called_once_with()
