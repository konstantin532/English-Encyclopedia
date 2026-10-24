"""Scope ordinary lesson checks without hiding experimental evidence globally."""
from .models import IndependentAttempt


def lesson_check_attempts(user):
    """Four-skill checks use variants 0–2; pilots have separate records/UI.

    Keep legacy empty-token lesson checks. Exclude experimental origins by
    both reserved variants and token prefixes, so one inconsistent marker
    cannot make pilot timing or a cafe transcript editable as a self-rating.
    Admin review and data export intentionally still use the full manager.
    """
    return (IndependentAttempt.objects.filter(
        user=user, skill__in=('meaning', 'writing', 'transfer', 'explain'),
        task_variant__in=(0, 1, 2),
    ).exclude(batch_token__startswith='pilot-')
      .exclude(batch_token__startswith='cafe-'))
