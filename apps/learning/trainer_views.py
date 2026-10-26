"""Private HTML boundary; only the service's allowlisted projection reaches templates."""
from functools import wraps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from urllib.parse import urlencode
from apps.learning import trainer_service as service
from apps.learning.trainer_content import PILOT_SLUG


def trainer_endpoint(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            if not getattr(settings, 'EE_VOCABULARY_TRAINER_ENABLED', False):
                raise Http404
            response = login_required(view)(request, *args, **kwargs)
        except Http404:
            response = HttpResponseNotFound('Эта встреча недоступна.')
        response['Cache-Control'] = 'private, no-store'
        response['Pragma'] = 'no-cache'
        response['Vary'] = 'Cookie'
        return response
    return wrapped


def page(request, *, state=None, error='', status=200, unsent=None, unsent_note=None):
    preferences = request.POST if request.method == 'POST' else request.GET
    context = {'state': state, 'error': error, 'lesson_slug': PILOT_SLUG,
               'summary': None if state else service.dashboard(request.user), 'unsent': unsent,
               'preferred_mode': preferences.get('mode', 'text'),
               'preferred_rating': preferences.get('self_rating', preferences.get('rating', '')),
               'unsent_note': unsent_note}
    if state:
        context['can_mnemonic'] = 'edit_note' in state['actions']
        context['notes_editor'] = context['can_mnemonic'] and (request.GET.get('notes') == '1' or unsent_note is not None)
        context['note_value'] = unsent_note if unsent_note is not None else state.get('personal_mnemonic', '')
    return render(request, 'learning/trainer.html', context, status=status)


@trainer_endpoint
@require_http_methods(['GET', 'POST'])
def trainer(request):
    if request.method == 'GET':
        return page(request)
    try:
        action = request.POST.get('action')
        if action == 'enroll':
            service.enroll(request.user, timezone_name=request.POST.get('timezone_name', 'Europe/Moscow'),
                           daily_limit=int(request.POST.get('daily_limit', '10')),
                           prerequisites_confirmed=request.POST.get('prerequisites') == 'yes')
        elif action == 'unenroll':
            service.unenroll(request.user)
        elif action == 'start':
            session = service.start_encounter(request.user, request.POST.get('uid', ''))
            return redirect('learning:trainer_session', session_id=session.pk)
        else:
            raise ValueError('Выберите действие на странице.')
    except (service.TrainerUnavailable, service.TrainerLimit) as exc:
        return page(request, error=str(exc), status=exc.status_code)
    except ValueError as exc:
        return page(request, error=str(exc), status=400)
    return redirect('learning:trainer')


@trainer_endpoint
@require_http_methods(['GET', 'POST'])
def encounter(request, session_id):
    try:
        state = service.encounter_view(request.user, session_id)
    except service.TrainerUnavailable:
        raise Http404 from None
    if request.method == 'GET':
        return page(request, state=state)
    answer = request.POST.get('answer', '')
    try:
        action = request.POST.get('action', '')
        service.perform_action(request.user, session_id, request.POST.get('token', ''),
                               int(request.POST.get('revision', '-1')), action, answer=answer,
                               mode=request.POST.get('mode', 'text'), self_rating=request.POST.get('self_rating', ''),
                               mnemonic=request.POST.get('mnemonic') if action == 'save_note' else None)
    except service.TrainerUnavailable:
        raise Http404 from None
    except (service.TrainerConflict, service.TrainerLimit) as exc:
        # An owner-scoped fresh projection is safe; keep the unconfirmed answer
        # separately so a conflict never overwrites it or becomes a learner error.
        return page(request, state=service.encounter_view(request.user, session_id), error=str(exc),
                    status=exc.status_code, unsent=answer,
                    unsent_note=request.POST.get('mnemonic') if request.POST.get('action') == 'save_note' else None)
    except ValueError as exc:
        return page(request, state=state, error=str(exc), status=400, unsent=answer,
                    unsent_note=request.POST.get('mnemonic') if request.POST.get('action') == 'save_note' else None)
    destination = reverse('learning:trainer_session', args=[session_id])
    preferences = {}
    if request.POST.get('action') == 'edit_note':
        preferences['notes'] = '1'
    if request.POST.get('mode') == 'spoken':
        preferences['mode'] = 'spoken'
    if request.POST.get('self_rating') in service.RATINGS:
        preferences['rating'] = request.POST['self_rating']
    if preferences:
        destination += '?' + urlencode(preferences)
    return redirect(destination)


@trainer_endpoint
@require_http_methods(['GET'])
def status(request, session_id):
    try:
        state = service.encounter_view(request.user, session_id)
    except service.TrainerUnavailable:
        raise Http404 from None
    return JsonResponse({'state': state, 'url': reverse('learning:trainer_session', args=[session_id])})
