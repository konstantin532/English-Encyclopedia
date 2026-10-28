"""Signed, bounded week-one results; existing learning services own progression."""
import hashlib
import json
import uuid

from django.core import signing

from apps.curriculum.models import Week
from apps.drills.models import Exercise, PracticeItem
from apps.drills.retry_guidance import is_open_pilot_response, is_pilot_exercise
from .models import ExerciseAttempt, ImportedGuestAnswer, UnitProgress, WeekGoal
from .services import record_attempt, record_practice
from .trainer_state import run_serialized

SALT = 'english-encyclopedia.guest-week-one.v1'
MAX_AGE = 30 * 24 * 60 * 60
MAX_ITEMS = 64
MAX_ANSWER = 200


def first_week(week):
    return bool(week and week.number == 1 and week.level.code == 'A1')


def in_scope(item):
    return bool(item.lesson.is_published and item.lesson.level.code == 'A1' and first_week(item.lesson.week))


def fingerprint(item):
    fields = ('answer', 'accepted', 'kind', 'stage', 'options', 'prompt_ru', 'prompt_en', 'order', 'review_of')
    content = {name: getattr(item, name, None) for name in fields}
    content['units'] = list(item.units.order_by('pk').values_list('pk', flat=True))
    content['lesson'] = item.lesson_id
    raw = json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def make_receipt(kind, item, answer):
    if not isinstance(answer, str) or len(answer) > MAX_ANSWER or not in_scope(item):
        return None
    correct = item.is_correct(answer)
    # Unmatched creative replies and translations need human comparison, not a false grade.
    if not correct and (kind == 'practice' or is_open_pilot_response(item)):
        return None
    payload = {'id': str(uuid.uuid4()), 'kind': kind, 'pk': item.pk,
               'answer': answer, 'fingerprint': fingerprint(item)}
    return {'key': f'{kind}:{item.pk}', 'complete': correct,
            'token': signing.dumps(payload, salt=SALT, compress=True)}


def make_goal_receipt(week, status):
    if not first_week(week) or status not in WeekGoal.GoalStatus.values:
        return None
    payload = {'id': str(uuid.uuid4()), 'kind': 'goal', 'pk': week.pk, 'answer': status}
    return {'key': f'goal:{week.pk}', 'complete': status == 'done', 'choice': status,
            'token': signing.dumps(payload, salt=SALT, compress=True)}


def import_results(user, tokens):
    if not user.is_authenticated:
        raise ValueError('Нужно войти в аккаунт.')
    if not isinstance(tokens, list) or len(tokens) > MAX_ITEMS or any(
            not isinstance(t, str) or len(t) > 4096 for t in tokens):
        raise ValueError('Некорректный список результатов.')

    def write():
        acknowledged, imported = [], 0
        for token in tokens:
            try:
                payload = signing.loads(token, salt=SALT, max_age=MAX_AGE)
                receipt_id = uuid.UUID(payload['id'])
                kind, pk, answer = payload['kind'], payload['pk'], payload['answer']
                if kind not in ('exercise', 'practice', 'goal') or type(pk) is not int or not isinstance(answer, str) or len(answer) > MAX_ANSWER:
                    raise ValueError('Invalid receipt')
                if kind == 'goal':
                    item = Week.objects.select_related('level').get(pk=pk)
                    if not first_week(item) or answer not in WeekGoal.GoalStatus.values:
                        raise ValueError('Invalid goal')
                else:
                    model = Exercise if kind == 'exercise' else PracticeItem
                    item = model.objects.select_related('lesson__week__level').get(pk=pk)
                    if not in_scope(item) or payload['fingerprint'] != fingerprint(item):
                        raise ValueError('Changed content')
                    correct = item.is_correct(answer)
                    if not correct and (kind == 'practice' or is_open_pilot_response(item)):
                        raise ValueError('Unverified answer')
            except (signing.BadSignature, KeyError, TypeError, ValueError, AttributeError, Week.DoesNotExist, Exercise.DoesNotExist, PracticeItem.DoesNotExist):
                # Invalid/expired/outdated receipts cannot be applied and need not retry forever.
                acknowledged.append(token)
                continue
            _, created = ImportedGuestAnswer.objects.get_or_create(user=user, receipt_id=receipt_id)
            if created:
                if kind == 'goal':
                    _, changed = WeekGoal.objects.get_or_create(user=user, week=item, defaults={'status': answer})
                elif kind == 'exercise':
                    existing = ExerciseAttempt.objects.filter(user=user, exercise=item)
                    changed = not (existing.filter(is_correct=True).exists() or (not correct and existing.exists()))
                    if changed:
                        pilot = is_pilot_exercise(item)
                        record_attempt(user, item, answer, delay_wrong_days=2 if pilot else 0)
                        if not correct and pilot:
                            from .mistake_review import schedule_review
                            schedule_review(user, item)
                else:
                    context = f'{item.lesson.slug}#t{item.order}'
                    contexts = UnitProgress.objects.filter(user=user, unit__in=item.units.all()).values_list('contexts_used', flat=True)
                    changed = not any(context in values for values in contexts)
                    if changed:
                        record_practice(user, item)
                imported += int(changed)
            acknowledged.append(token)
        return {'acknowledged': acknowledged, 'imported': imported}
    return run_serialized(user, write)
