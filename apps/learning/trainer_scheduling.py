"""One eligibility decision per encounter, using the existing UnitProgress."""
from datetime import timedelta

from .models import IndependentAttempt, Status, TrainerSession, UnitProgress

MIN_DELAY = timedelta(hours=24)
LADDER = (1, 3, 7, 14)


def schedule_recall(session, assessment, mode, now):
    progress, _ = UnitProgress.objects.get_or_create(user=session.user, unit=session.unit)
    if mode == 'text' and assessment['outcome'] == 'correct':
        progress.correct_count += 1
    elif mode == 'text' and assessment['outcome'] == 'incorrect':
        progress.wrong_count += 1
    previous = (TrainerSession.objects.filter(user=session.user, unit=session.unit, last_material_at__isnull=False)
                .exclude(pk=session.pk).order_by('-last_material_at').first())
    delayed = bool(previous and previous.last_material_at and
                   now - previous.last_material_at >= MIN_DELAY)
    due = progress.next_review_at is None or progress.next_review_at <= now
    # Family alternation is checked independently of task identity and snapshots.
    last_recall = (IndependentAttempt.objects.filter(user=session.user, target=session.unit,
                   origin='trainer', skill='recall').exclude(trainer_session=session)
                   .order_by('-created_at', '-pk').first())
    fresh_family = not last_recall or last_recall.evidence.get('family_id') != session.family_id
    eligible = (not session.is_initial and not session.schedule_applied and due and delayed
                and fresh_family and not session.assistance and mode == 'text'
                and session.recall_tries == 1 and assessment['outcome'] == 'correct')
    if session.schedule_applied:
        reason = 'already_scheduled'
    elif session.is_initial:
        reason = 'initial_exposure'
    elif not due:
        reason = 'early_practice'
    elif not delayed:
        reason = 'minimum_delay'
    elif session.assistance:
        reason = 'assisted'
    elif mode == 'spoken':
        reason = 'self_reported'
    elif not fresh_family:
        reason = 'same_family'
    elif eligible:
        reason = 'delayed_correct'
    else:
        reason = assessment['outcome']
    if not session.schedule_applied:
        if progress.next_review_at is None:
            progress.next_review_at = now + MIN_DELAY
        if due:
            if eligible:
                progress.stage = min(progress.stage + 1, 4)
                progress.next_review_at = now + timedelta(days=LADDER[max(0, progress.stage - 1)])
                context = 'trainer:' + session.family_id
                if context not in progress.contexts_used:
                    progress.contexts_used = [*progress.contexts_used, context]
            else:
                if not session.is_initial and assessment['outcome'] == 'incorrect' and mode == 'text':
                    progress.stage = max(0, progress.stage - 1)
                progress.next_review_at = now + MIN_DELAY
        session.schedule_applied = True
    # This workflow does not award independent-use/mastery/CEFR statuses.
    if (progress.status == Status.NEW and mode == 'text'
            and assessment['outcome'] == 'correct' and not session.assistance):
        progress.status = Status.RECOGNITION
    progress.save()
    return {'scheduling': reason, 'schedule_eligible': bool(eligible)}
