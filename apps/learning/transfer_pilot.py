"""Opt-in, non-graded week 1–2 transfer/retention pilot.

Reuses IndependentAttempt and the existing staff review workflow. Each stage
uses a different situation; attempts never award CEFR/UnitProgress mastery.
"""
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.lessons.models import Lesson
from .models import IndependentAttempt

# Reserve 100–102 to keep existing independent-check variants (0–2) intact.
STAGES = (("initial", 100, 0), ("day_7", 101, 7), ("day_30", 102, 30))
PILOTS = {
    "a1-verb-be": {
        "week": 1, "skill": "introduce_self",
        "title": "Неделя 1 · знакомство",
        "missions": (
            {
                "prompt": "Представьте: вы впервые встречаете соседа. Поздоровайтесь, "
                          "назовите вымышленное имя и скажите, откуда вы. Напишите по-английски 1–3 короткие фразы.",
                "model": "Hello! I'm Alex. I'm from Boston.",
            },
            {
                "prompt": "Новый ученик переехал в ваш дом и спрашивает, кто вы. "
                          "Представьтесь и скажите, что вы его сосед. Используйте вымышленное имя.",
                "model": "Hi! My name is Sam. I'm your neighbor.",
            },
            {
                "prompt": "Вам нужно познакомиться с человеком на встрече. "
                          "Представьтесь и вежливо спросите, как его зовут. Используйте вымышленное имя.",
                "model": "Hello, I'm Kim. What's your name?",
            },
        ),
    },
    "a1-have-like-can-do": {
        "week": 2, "skill": "describe_home",
        "title": "Неделя 2 · мой новый дом",
        "missions": (
            {
                "prompt": "Вы показываете гостю комнату. Назовите вещь, которая у вас есть, "
                          "и скажите, нравится ли она вам. Используйте вымышленные сведения.",
                "model": "I have a new book. I like it.",
            },
            {
                "prompt": "Сосед спрашивает, что у вас есть дома. Ответьте двумя короткими "
                          "английскими фразами: назовите предмет и скажите о нём что-нибудь.",
                "model": "I have a small table. It is new.",
            },
            {
                "prompt": "Гость впервые у вас дома. Покажите одну вещь и вежливо предложите "
                          "воду. Напишите 1–3 простые английские фразы.",
                "model": "This is my room. Do you like it?",
            },
        ),
    },
}


def attempts_for(user, lesson):
    """Experimental attempts are a separate evidence lane, never ordinary practice."""
    return IndependentAttempt.objects.filter(
        user=user, lesson=lesson, skill="transfer",
        task_variant__in=[stage[1] for stage in STAGES],
        batch_token__startswith="pilot-",
    ).order_by("created_at", "pk")


def next_stage(rows, now):
    """Return stage, due time; stage 7 and 30 are measured from the *initial* attempt."""
    by_variant = {row.task_variant: row for row in rows}
    first = by_variant.get(100)
    if first is None:
        return STAGES[0], None
    for stage in STAGES[1:]:
        if stage[1] not in by_variant:
            return stage, first.created_at + timedelta(days=stage[2])
    return None, None


@login_required
@require_http_methods(["GET", "POST"])
def transfer_pilot(request, slug):
    if slug not in PILOTS:
        return HttpResponseBadRequest("Эксперимент открыт только для двух первых недель A1.")
    pilot = PILOTS[slug]
    lesson = get_object_or_404(
        Lesson, slug=slug, level__code="A1", is_published=True,
    )
    rows = list(attempts_for(request.user, lesson))
    stage, due_at = next_stage(rows, timezone.now())
    now = timezone.now()
    ready = stage is not None and (due_at is None or due_at <= now)
    token_key = f"transfer_pilot_{lesson.pk}_{stage[1]}" if stage else None
    if token_key and ready and token_key not in request.session:
        request.session[token_key] = "pilot-" + secrets.token_urlsafe(22)

    if request.method == "POST":
        if not ready or stage is None or not token_key:
            return HttpResponseBadRequest("Новая проверка пока не открыта.")
        expected = request.session.get(token_key, "")
        supplied = request.POST.get("token", "")
        if not expected or not supplied or not secrets.compare_digest(expected, supplied):
            return HttpResponseBadRequest("Попытка уже отправлена либо форма устарела.")
        if request.POST.get("stage") != str(stage[1]):
            return HttpResponseBadRequest("Этап проверки изменился: обновите страницу.")
        answer = request.POST.get("answer", "")
        assistance = request.POST.get("assistance", "")
        if (not isinstance(answer, str) or not answer.strip() or len(answer) > 400
                or assistance not in (
                    IndependentAttempt.Assistance.NO_HELP,
                    IndependentAttempt.Assistance.NOTES,
                    IndependentAttempt.Assistance.TRANSLATOR,
                )):
            return HttpResponseBadRequest("Напишите ответ до 400 символов и укажите использованную помощь.")
        mission = pilot["missions"][STAGES.index(stage)]
        try:
            with transaction.atomic():
                # Serialize same-user requests on PostgreSQL; DB uniqueness also
                # rejects cross-device concurrent double submissions.
                get_user_model().objects.select_for_update().get(pk=request.user.pk)
                IndependentAttempt.objects.create(
                    user=request.user, lesson=lesson, skill="transfer",
                    submitted=answer.strip(),
                    outcome=IndependentAttempt.Outcome.SELF_REPORTED,
                    assistance=assistance, task_variant=stage[1],
                    batch_token=expected,
                    prompt_snapshot=mission["prompt"],
                    model_snapshot=mission["model"],
                )
        except IntegrityError:
            return HttpResponseBadRequest("Этот этап уже выполнен; повторная отправка не записана.")
        request.session.pop(token_key, None)
        return redirect("learning:transfer_pilot", slug=slug)

    return render(request, "learning/transfer_pilot.html", {
        "lesson": lesson, "pilot": pilot, "attempts": rows,
        "stage": stage, "due_at": due_at, "ready": ready,
        "mission": pilot["missions"][STAGES.index(stage)] if ready else None,
        "token": request.session.get(token_key, "") if ready else "",
        "completed": stage is None,
        "now": now,
    })
