"""Opt-in trainer: persisted encounter state and safe, phase-specific projections.

All mutation entry points use the same user gate as legacy lexical services.
No caller-supplied grade, interval, target, family or assistance claim is trusted.
"""
import hashlib
import json
from datetime import datetime, time, timedelta, timezone as datetime_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit
from .models import (IndependentAttempt, PersonalMnemonic, TrainerEnrollment,
                     TrainerSession, UnitProgress, trainer_token)
from .trainer_content import PILOT_SLUG, UNIT_UIDS, assess_recall, pilot_content
from .trainer_scheduling import MIN_DELAY, schedule_recall
from .trainer_state import (TrainerConflict, TrainerLimit, TrainerUnavailable,
                            enabled, require_user, serialized, trainer_mutation)

RATINGS = ('good', 'hard', 'again')
SCHEDULE_LABELS = {
    'initial_exposure': 'Знакомство — это ещё не отсроченное вспоминание.',
    'early_practice': 'Это ранняя практика: прежний срок повторения сохранён.',
    'minimum_delay': 'После последнего показа ещё не прошло 24 часа.',
    'assisted': 'Ответ с зарегистрированной помощью: ступень не повышена.',
    'self_reported': 'Устная самооценка: автоматической проверки речи нет.',
    'same_family': 'Повтор той же ситуации не повышает ступень.',
    'delayed_correct': 'Удалось вспомнить проверенный вариант после перерыва.',
    'incorrect': 'Нужна практика; следующая встреча не раньше чем через 24 часа.',
    'uncertain': 'Вариант требует самостоятельного сравнения, это не подтверждённая ошибка.',
    'already_scheduled': 'Расписание этой встречи уже сохранено.',
}


def _now(value):
    value = value or timezone.now()
    if not isinstance(value, datetime) or timezone.is_naive(value):
        raise ValueError('Нужно время с часовым поясом.')
    return value.astimezone(datetime_timezone.utc)


def _enrollment(user):
    require_user(user)
    enrollment = TrainerEnrollment.objects.filter(user=user, enabled=True, prerequisites_confirmed=True).first()
    if enrollment is None:
        raise TrainerUnavailable('Сначала включите тренажёр после знакомства с уроком №5.')
    return enrollment


def _session(user, session_id):
    try:
        session = TrainerSession.objects.select_related('unit').filter(pk=session_id, user=user).first()
    except (ValueError, TypeError):
        session = None
    if session is None:
        raise TrainerUnavailable('Эта встреча недоступна.')
    return session


def _rate(enrollment, now):
    if enrollment.rate_window_at is None or now - enrollment.rate_window_at >= timedelta(minutes=1):
        enrollment.rate_window_at = now
        enrollment.rate_count = 0
    if enrollment.rate_count >= 60:
        raise TrainerLimit('Слишком много действий. Подождите минуту и продолжите.')
    enrollment.rate_count += 1
    enrollment.save(update_fields=['rate_window_at', 'rate_count'])


def _local_bounds(enrollment, now):
    zone = ZoneInfo(enrollment.timezone_name)
    today = now.astimezone(zone).date()
    start = datetime.combine(today, time.min, zone)
    end = datetime.combine(today + timedelta(days=1), time.min, zone)
    return start, end


def _budget_used(user, enrollment, now):
    start, end = _local_bounds(enrollment, now)
    return TrainerSession.objects.filter(user=user, started_at__gte=start, started_at__lt=end).count()


@trainer_mutation
def enroll(user, *, timezone_name='Europe/Moscow', daily_limit=10, prerequisites_confirmed=False):
    require_user(user)
    if prerequisites_confirmed is not True:
        raise TrainerUnavailable('Подтвердите знакомство с уроком №5 «Заказ в кафе».')
    if type(daily_limit) is not int or not 1 <= daily_limit <= 10:
        raise ValueError('Выберите от 1 до 10 встреч в день.')
    try:
        ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        raise ValueError('Выберите действующий часовой пояс IANA.') from None
    try:
        pilot_content()
    except ValueError as exc:
        raise TrainerUnavailable('Контент тренажёра пока недоступен.') from exc
    enrollment, _ = TrainerEnrollment.objects.update_or_create(user=user, defaults={
        'enabled': True, 'prerequisites_confirmed': True, 'timezone_name': timezone_name,
        'daily_limit': daily_limit,
    })
    return enrollment


@trainer_mutation
def unenroll(user):
    require_user(user)
    TrainerEnrollment.objects.filter(user=user).update(enabled=False)


def legacy_managed_units(user):
    # Important for rollout: the disabled flag never queries additive tables.
    if not enabled() or not user.is_authenticated:
        return set()
    if TrainerEnrollment.objects.filter(user=user, enabled=True, prerequisites_confirmed=True).exists():
        return set(UNIT_UIDS)
    return set()


@serialized
def register_legacy_exposure(user, units, *, now=None):
    """Register delivery of our site's target material, without scheduling it.

    Call before returning a model/answer/page that contains these LexicalUnits.
    `units` is an iterable of LexicalUnit objects or UID strings. No enrollment
    or session is created; unrelated users/units and the disabled flag are inert.
    """
    managed = legacy_managed_units(user)
    if not managed:
        return
    uids = {getattr(unit, 'uid', unit) for unit in units} & managed
    now = _now(now)
    for uid in sorted(uids):
        session = (TrainerSession.objects.filter(user=user, unit__uid=uid)
                   .order_by('-started_at', '-pk').first())
        if session is None:
            continue
        if session.completed_at is None and 'legacy_model' not in session.assistance:
            session.assistance = [*session.assistance, 'legacy_model']
        if session.last_material_at is None or now > session.last_material_at:
            session.last_material_at = now
        session.save(update_fields=['assistance', 'last_material_at'])


def dashboard(user, *, now=None):
    if not enabled() or not user.is_authenticated:
        return {'available': False}
    now = _now(now)
    enrollment = TrainerEnrollment.objects.filter(user=user, enabled=True, prerequisites_confirmed=True).first()
    if enrollment is None:
        return {'available': True, 'enrolled': False}
    try:
        document = pilot_content()
    except ValueError:
        return {'available': False}
    progress = {p.unit.uid: p for p in UnitProgress.objects.filter(user=user, unit__uid__in=UNIT_UIDS).select_related('unit')}
    sessions = {s.unit.uid: s for s in TrainerSession.objects.filter(user=user, completed_at__isnull=True).select_related('unit')}
    units = []
    for index, unit in enumerate(document['units']):
        item = progress.get(unit['uid'])
        session = sessions.get(unit['uid'])
        due = item.next_review_at if item else None
        state = 'new' if item is None else ('due' if due is None or due <= now else 'later')
        latest = TrainerSession.objects.filter(user=user, unit__uid=unit['uid']).order_by('-started_at', '-pk').first()
        needs_practice = bool(latest and latest.result and latest.result.get('scheduling') not in
                              ('delayed_correct', 'initial_exposure', 'early_practice'))
        units.append({'uid': unit['uid'], 'label': f'Единица {index + 1}', 'state': state,
                      'needs_practice': needs_practice, 'next_review_at': due.isoformat() if due else None,
                      'session_id': session.pk if session else None})
    units.sort(key=lambda u: (0 if u['state'] == 'due' else 1 if u['state'] == 'new' else 2,
                              u['next_review_at'] or '', UNIT_UIDS.index(u['uid'])))
    return {'available': True, 'enrolled': True, 'units': units,
            'timezone_name': enrollment.timezone_name, 'daily_limit': enrollment.daily_limit,
            'remaining': max(0, enrollment.daily_limit - _budget_used(user, enrollment, now))}


@trainer_mutation
def start_encounter(user, uid, *, now=None):
    enrollment = _enrollment(user)
    now = _now(now)
    if uid not in UNIT_UIDS:
        raise TrainerUnavailable('Эта единица не входит в пилот.')
    existing = TrainerSession.objects.filter(user=user, unit__uid=uid, completed_at__isnull=True).first()
    if existing:
        return existing
    if _budget_used(user, enrollment, now) >= enrollment.daily_limit:
        raise TrainerLimit('Лимит встреч на сегодня достигнут. Продолжим завтра.')
    try:
        document = pilot_content()
        content = next(u for u in document['units'] if u['uid'] == uid)
        unit = LexicalUnit.objects.get(uid=uid)
        Lesson.objects.get(slug=PILOT_SLUG, is_published=True)
    except (ValueError, StopIteration, LexicalUnit.DoesNotExist, Lesson.DoesNotExist) as exc:
        raise TrainerUnavailable('Контент тренажёра пока недоступен.') from exc
    previous = TrainerSession.objects.filter(user=user, unit=unit).order_by('-started_at', '-pk').first()
    # Different authored family, not a cosmetic variant of the same question.
    index = next((i for i, t in enumerate(content['recall_tasks'])
                  if not previous or t['family_id'] != previous.family_id), 0)
    task = content['recall_tasks'][index]
    # A new assessment revision establishes fresh evidence even if an explicit
    # editorial task mapping exists. Historical rows are never reclassified.
    initial = previous is None or previous.assessment_revision != document['assessment_revision']
    progress, _ = UnitProgress.objects.get_or_create(user=user, unit=unit)
    if progress.next_review_at is None:
        progress.next_review_at = now + MIN_DELAY
        progress.save(update_fields=['next_review_at', 'updated_at'])
    _rate(enrollment, now)
    return TrainerSession.objects.create(
        user=user, unit=unit, phase='intro' if initial else 'recall', is_initial=initial,
        snapshot=content, content_version=document['content_version'],
        assessment_revision=document['assessment_revision'], task_id=task['task_id'],
        family_id=task['family_id'], application_index=index, started_at=now, updated_at=now,
        last_material_at=now if initial else None,
    )


def _projection(session):
    """Explicit allowlist: never serialize a model or its frozen private snapshot."""
    content = session.snapshot
    task = next(t for t in content['recall_tasks'] if t['task_id'] == session.task_id)
    application = content['applications'][session.application_index]
    result = {'session_id': session.pk, 'uid': session.unit.uid, 'phase': session.phase,
              'revision': session.revision, 'token': session.token,
              'content_version': session.content_version, 'assistance': list(session.assistance),
              'recall_tries': session.recall_tries, 'draft': session.draft,
              'actions': [], 'spoken_note': 'Речь не записывается и не проверяется автоматически. Это самооценка.'}
    if session.phase == 'intro':
        result.update(title=content['title'], explanation=content['explanation'], examples=content['examples'],
                      mnemonic=content['mnemonic'], mnemonic_note=content['reviewer_note'], actions=['begin'])
    elif session.phase == 'recall':
        result.update(prompt=task['prompt'], actions=['recall', 'dont_know', 'hint', 'reveal', 'save_draft'])
        if session.recall_tries:
            result['feedback'] = 'Пока не получилось. Можно попробовать ещё раз или открыть образец.'
        if 'hint' in session.assistance:
            result.update(mnemonic=content['mnemonic'], mnemonic_note=content['reviewer_note'])
        if 'reveal' in session.assistance:
            result['model'] = task['model']
    elif session.phase == 'spoken_compare':
        result.update(prompt=task['prompt'], model=task['model'], comparison=content['spoken']['comparison'],
                      actions=['rate_spoken'])
    elif session.phase == 'feedback':
        result.update(prompt=task['prompt'], model=task['model'], result=session.result,
                      feedback=session.result.get('feedback', ''), actions=['continue'])
    elif session.phase == 'application':
        result.update(prompt=application['prompt'], criteria=application['criteria'],
                      actions=['apply', 'reveal_application', 'save_draft'])
        if 'application_model' in session.assistance:
            result['valid_examples'] = application['valid_examples']
    elif session.phase == 'complete':
        progress = UnitProgress.objects.filter(user_id=session.user_id, unit_id=session.unit_id).first()
        result.update(valid_examples=application['valid_examples'], criteria=application['criteria'],
                      result=session.result, next_review_at=(progress.next_review_at.isoformat()
                          if progress and progress.next_review_at else None))
    if session.phase not in ('complete', 'abandoned'):
        result['actions'].append('abandon')
    if session.phase in ('intro', 'feedback', 'complete') or 'hint' in session.assistance:
        mnemonic = PersonalMnemonic.objects.filter(user_id=session.user_id, unit_id=session.unit_id).first()
        result['personal_mnemonic'] = mnemonic.text if mnemonic else ''
    if session.result and session.phase in ('feedback', 'complete'):
        result['schedule_reason'] = SCHEDULE_LABELS.get(session.result.get('scheduling'), '')
    return result


def _delivery(session, now):
    result = _projection(session)
    if any(key in result for key in ('model', 'examples', 'valid_examples', 'mnemonic')):
        if session.last_material_at is None or now > session.last_material_at:
            session.last_material_at = now
            session.save(update_fields=['last_material_at'])
        active = (TrainerSession.objects.filter(
            user_id=session.user_id, unit_id=session.unit_id, completed_at__isnull=True,
        ).exclude(pk=session.pk).first())
        if active is not None:
            # Reading an older model while a new assessment is open remains
            # help for that whole assessment, even if the learner waits 24h.
            if 'history_model' not in active.assistance:
                active.assistance = [*active.assistance, 'history_model']
            if active.last_material_at is None or now > active.last_material_at:
                active.last_material_at = now
            active.save(update_fields=['assistance', 'last_material_at'])
    return result


def _conflict_state(session):
    # An exception rolls back its transaction. Do not reveal material here:
    # the client follows the canonical identity with a fresh tracked GET.
    view = _projection(session)
    return {key: view[key] for key in ('session_id', 'uid', 'revision', 'token', 'phase', 'actions')}


@trainer_mutation
def encounter_view(user, session_id, *, now=None):
    _enrollment(user)
    return _delivery(_session(user, session_id), _now(now))


def _record(session, answer, mode, self_rating, assessment, now, *, application=False):
    content = session.snapshot
    task = (content['applications'][session.application_index] if application else
            next(t for t in content['recall_tasks'] if t['task_id'] == session.task_id))
    decision = ({'schedule_eligible': False, 'scheduling': 'application_self_report'} if application else
                schedule_recall(session, assessment, mode, now))
    assessment.update(decision)
    evidence = {
        'task_id': task['task_id'], 'family_id': session.family_id,
        'content_version': session.content_version, 'assessment_revision': session.assessment_revision,
        'kind': ('open_application' if application else 'initial_recall' if session.is_initial else 'delayed_recall'),
        'mode': mode, 'reliability': 'self_report' if application or mode == 'spoken' else 'constrained_model_check',
        'assistance': list(session.assistance), 'goal_achieved': assessment.get('goal_achieved'),
        'target_used': assessment.get('target_used'), **decision,
    }
    IndependentAttempt.objects.create(
        user=session.user, lesson=Lesson.objects.get(slug=PILOT_SLUG), origin='trainer', target=session.unit,
        trainer_session=session, trainer_sequence=1 if application else session.recall_tries,
        skill='application' if application else 'recall', submitted=answer,
        prompt_snapshot=task['prompt'], model_snapshot='\n'.join(task['valid_examples']) if application else task['model'],
        outcome=('self_reported' if application or mode == 'spoken' else
                 'model_match' if assessment['outcome'] == 'correct' else 'needs_review'),
        self_rating=self_rating, assistance=IndependentAttempt.Assistance.NOT_STATED,
        batch_token='trainer-' + session.token, evidence=evidence, created_at=now,
    )
    return assessment


@trainer_mutation
def perform_action(user, session_id, token, revision, action, *, answer='', mode='text', self_rating='', now=None):
    enrollment = _enrollment(user)
    now = _now(now)
    session = _session(user, session_id)
    if not isinstance(answer, str) or len(answer) > 400:
        raise ValueError('Ответ или черновик должен содержать не больше 400 символов.')
    if mode not in ('text', 'spoken') or self_rating not in ('', *RATINGS):
        raise ValueError('Неизвестный способ ответа или самооценка.')
    payload = [revision, action, answer, mode, self_rating]
    fingerprint = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
    receipt = session.receipts.get(str(token))
    if receipt:
        if receipt['fingerprint'] != fingerprint:
            raise TrainerConflict('Этот запрос уже принят с другим ответом.', canonical=_conflict_state(session))
        # Replay acknowledges the same operation but uses the canonical current
        # phase, preventing old model feedback leaking into a later assessment.
        return _delivery(session, now)
    if type(revision) is not int or revision != session.revision or token != session.token:
        raise TrainerConflict(canonical=_conflict_state(session))
    if action not in _projection(session)['actions']:
        raise TrainerConflict('Это действие недоступно на текущем шаге.', canonical=_conflict_state(session))
    _rate(enrollment, now)
    if action == 'begin':
        session.phase = 'recall'
    elif action == 'save_draft':
        session.draft = answer
        session.draft_updated_at = now
    elif action in ('hint', 'reveal', 'reveal_application'):
        marker = 'application_model' if action == 'reveal_application' else action
        if marker not in session.assistance:
            session.assistance = [*session.assistance, marker]
        session.last_material_at = now
        if answer:
            session.draft = answer
            session.draft_updated_at = now
    elif action == 'dont_know':
        session.recall_tries += 1
        result = assess_recall(session.snapshot, '', task_id=session.task_id)
        result['feedback'] = 'Не вспомнить сейчас — нормально. Посмотрите образец и попробуйте применить его.'
        session.result = _record(session, '', 'text', '', result, now)
        session.phase = 'feedback'
        session.last_material_at = now
        session.draft = ''
    elif action == 'recall':
        if session.recall_tries >= 2:
            raise TrainerConflict(canonical=_conflict_state(session))
        if mode == 'spoken':
            if answer:
                session.draft = answer
                session.draft_updated_at = now
            session.phase = 'spoken_compare'
            session.last_material_at = now
        else:
            if not answer.strip():
                raise ValueError('Напишите ответ или откройте образец, если не помните.')
            if session.recall_tries:
                session.assistance = [*session.assistance, 'retry']
            session.recall_tries += 1
            result = assess_recall(session.snapshot, answer, task_id=session.task_id)
            session.result = _record(session, answer, mode, '', result, now)
            session.phase = 'recall' if result['outcome'] == 'incorrect' and session.recall_tries < 2 else 'feedback'
            if session.phase == 'feedback':
                session.last_material_at = now
            session.draft = ''
    elif action == 'rate_spoken':
        if self_rating not in RATINGS:
            raise ValueError('Выберите самооценку после сравнения.')
        session.recall_tries += 1
        session.result = _record(session, '', 'spoken', self_rating, {
            'outcome': 'self_reported', 'goal_achieved': None, 'target_used': None,
            'feedback': 'Вы сравнили свой ответ с образцом. Это самооценка, а не проверка речи.'}, now)
        session.phase = 'feedback'
        session.last_material_at = now
        session.draft = ''
    elif action == 'continue':
        session.phase = 'application'
    elif action == 'apply':
        if self_rating not in RATINGS or mode == 'text' and not answer.strip():
            raise ValueError('Добавьте свой ответ и самооценку; для речи достаточно самооценки.')
        _record(session, answer if mode == 'text' else '', mode, self_rating,
                {'outcome': 'self_reported', 'goal_achieved': None, 'target_used': None}, now, application=True)
        session.phase = 'complete'
        session.completed_at = now
        session.last_material_at = now
        session.draft = ''
    elif action == 'abandon':
        session.phase = 'abandoned'
        session.completed_at = now
        session.draft = ''
    session.revision += 1
    session.token = trainer_token()
    session.updated_at = now
    # Store only a fingerprint and confirmation metadata, never unsent text in a
    # receipt: draft cleanup must actually erase that text from all stored fields.
    session.receipts = {**session.receipts, str(token): {'fingerprint': fingerprint, 'revision': session.revision}}
    session.save()
    return _delivery(session, now)


@trainer_mutation
def save_mnemonic(user, uid, text):
    enrollment = _enrollment(user)
    if not isinstance(text, str) or len(text) > 300:
        raise ValueError('Личная мнемоника — обычный текст до 300 символов.')
    if uid not in UNIT_UIDS:
        raise TrainerUnavailable('Эта единица не входит в пилот.')
    unit = LexicalUnit.objects.filter(uid=uid).first()
    if unit is None:
        raise TrainerUnavailable('Эта единица недоступна.')
    _rate(enrollment, timezone.now())
    mnemonic, _ = PersonalMnemonic.objects.update_or_create(user=user, unit=unit, defaults={'text': text})
    return mnemonic
