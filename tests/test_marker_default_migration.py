"""Marker visibility survives upgrades and historical-model inserts."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from apps.accounts.models import User


class MarkerDefaultMigrationTests(TransactionTestCase):
    serialized_rollback = True

    def test_upgrade_preserves_existing_preferences_and_defaults_legacy_inserts(self):
        previous = ('accounts', '0001_initial')
        added = ('accounts', '0002_markers_enabled')
        target = ('accounts', '0003_markers_enabled_db_default')
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([previous])
            old_user = executor.loader.project_state([previous]).apps.get_model('accounts', 'User')
            for color in (False, True):
                old_user.objects.create(email=f'existing-{color}@example.test', markers_in_color=color)

            executor = MigrationExecutor(connection)
            executor.migrate([added])
            added_user = executor.loader.project_state([added]).apps.get_model('accounts', 'User')
            disabled = added_user.objects.create(email='already-upgraded@example.test', markers_in_color=False)
            self.assertFalse(disabled.markers_enabled)

            executor = MigrationExecutor(connection)
            executor.migrate([target])
            # Модель «той эпохи»: у текущей User могут быть поля из более поздних миграций.
            target_user = executor.loader.project_state([target]).apps.get_model('accounts', 'User')
            for color in (False, True):
                saved = target_user.objects.get(email=f'existing-{color}@example.test')
                self.assertTrue(saved.markers_enabled)
                self.assertEqual(saved.markers_in_color, color)
            saved = target_user.objects.get(pk=disabled.pk)
            self.assertFalse(saved.markers_enabled)
            self.assertFalse(saved.markers_in_color)

            # Other apps' older migration states do not know markers_enabled.
            # Their inserts must still work after the accounts upgrade.
            legacy = old_user.objects.create(email='historical-insert@example.test', markers_in_color=False)
            saved = target_user.objects.get(pk=legacy.pk)
            self.assertFalse(saved.markers_enabled)
            self.assertFalse(saved.markers_in_color)
            MigrationExecutor(connection).migrate(latest)
            fresh = User.objects.create_user('fresh-default@example.test')
            self.assertFalse(fresh.markers_enabled)
        finally:
            MigrationExecutor(connection).migrate(latest)
