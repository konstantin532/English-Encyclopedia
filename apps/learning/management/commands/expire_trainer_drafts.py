"""Scrub only inactive unsent text; confirmed attempts and snapshots survive."""
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.learning.models import TrainerSession
from apps.learning.trainer_state import run_serialized


class Command(BaseCommand):
    help = 'Удалить неотправленные черновики тренажёра старше 30 дней.'

    def add_arguments(self, parser):
        parser.add_argument('--now', help='Время ISO 8601 с часовым поясом (для воспроизводимой проверки).')

    def handle(self, *args, **options):
        try:
            now = datetime.fromisoformat(options['now']) if options.get('now') else timezone.now()
        except ValueError as exc:
            raise CommandError('Нужно время ISO 8601.') from exc
        if timezone.is_naive(now):
            raise CommandError('Нужен часовой пояс.')
        cutoff = now - timedelta(days=30)

        def scrub():
            expired = TrainerSession.objects.filter(draft_updated_at__lt=cutoff).exclude(draft='')
            owners = expired.order_by('user_id').values_list('user_id', flat=True).distinct()
            count = 0
            for user_id in list(owners):
                # Only the owner ID is needed for the gate; no auth field is read
                # or changed. Recheck expiry after locking to preserve fresh edits.
                owner = get_user_model()(pk=user_id)
                count += run_serialized(owner, lambda: expired.filter(user_id=user_id).update(
                    draft='', draft_updated_at=None))
            return count

        # Retry the whole maintenance transaction if the initial SQLite scan or
        # its write upgrade is locked. User gates prevent stale draft resurrection.
        count = run_serialized(AnonymousUser(), scrub)
        self.stdout.write(f'Удалено черновиков: {count}')
