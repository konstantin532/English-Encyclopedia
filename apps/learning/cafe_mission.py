"""A1 café information-gap pilot: server-owned stock, constrained dialogue, human review.

The closed dialogue rules recognise a *small* set of meaningful A1 utterances.
They do not grade free English, pronunciation, CEFR, or individual mastery.
"""
import re
import secrets

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.lessons.models import Lesson
from .models import IndependentAttempt

SESSION_KEY = "learning_cafe_mission_v1"
VERSION = "cafe-gap-1"
# A tiny editorially reviewed micro-skill map, not a psychometric skill model.
SKILLS = {
    "cafe.order_one": {"can_do": "Я могу попросить одну порцию", "requires": ()},
    "cafe.ask_options": {"can_do": "Я могу спросить, что есть в наличии",
                         "requires": ("cafe.order_one",)},
    "cafe.choose": {"can_do": "Я могу попросить замену",
                    "requires": ("cafe.ask_options",)},
    "cafe.repair": {"can_do": "Я могу исправить неверно услышанное количество",
                    "requires": ("cafe.choose",)},
}
SCENARIOS = (
    {"wanted": "tea", "available": ("coffee", "water")},
    {"wanted": "coffee", "available": ("tea", "water")},
)
HINTS = {
    "order": "Вежливая просьба: I'd like one ..., please.",
    "ask": "Как узнать варианты? What do you have?",
    "choose": "Форма новой просьбы: Can I have one ..., please?",
    "repair": "Как исправить количество? No, one ..., please.",
}
MAX_TURNS = 9
MAX_HINTS = 3


def parse_order(value):
    """Return a narrow, unambiguous request (quantity, drink), or None.

    The intent must be an actual positive request, not merely a drink mention.
    Unrecognised expressions are referred to retry/human review, never 'wrong'.
    """
    text = re.sub(r"[?!.,;:]+", " ", value.casefold().replace("’", "'"))
    text = re.sub(r"\s+", " ", text).strip()
    positive = re.match(
        r"^(?:i(?: would|'d) like|(?:can|could|may) i have|"
        r"please (?:can|could) i have|(?:one|two|three|a) )\b", text
    )
    if not positive or re.search(r"\b(?:don't|not|never)\b", text):
        return None
    drinks = re.findall(r"\b(tea|coffee|water)s?\b", text)
    if len(drinks) != 1:
        return None
    quantities = re.findall(r"\b(one|two|three|a|an)\b", text)
    if len(quantities) > 1:
        return None
    qty = {"one": 1, "a": 1, "an": 1, "two": 2, "three": 3}.get(
        quantities[0], 1
    ) if quantities else 1
    return qty, drinks[0]


def asks_for_options(value):
    text = value.casefold()
    return bool(re.search(
        r"\b(?:what (?:do you have|is available|else|have you got)|"
        r"what can i (?:have|order)|do you have (?:anything|something) else)\b",
        text,
    ))


def corrects_one(value, drink):
    text = value.casefold().replace("’", "'")
    return bool(re.search(r"\b(?:no|sorry)\b", text)
                and re.search(r"\b(?:one|a)\s+" + re.escape(drink) + r"\b", text)
                # A negated request is not evidence of correcting an order.
                # Keep the recognizer conservative: ambiguous replies get a retry.
                and not re.search(
                    r"\b(?:two|three|yes|not|never|don't|doesn't|didn't|can't|cannot|won't|wouldn't)\b",
                    text,
                ))


def start_state(user_id):
    index = secrets.randbelow(len(SCENARIOS))
    return {
        "version": VERSION, "scenario": index, "phase": "order",
        "owner_id": user_id,
        "nonce": secrets.token_urlsafe(24), "turns": 0, "hints": 0,
        "observed": [], "accepted": [], "saved_id": None,
        "feedback": "", "messages": [
            {"who": "Mia", "text": "Good morning! What would you like?"}
        ],
    }


def advance(state, answer):
    """Advance only for transparent A1 acts. No open-response correctness score."""
    scenario = SCENARIOS[state["scenario"]]
    phase = state["phase"]
    order = parse_order(answer)
    message = None
    skill = None
    if phase == "order":
        if order and order[1] == scenario["wanted"] and order[0] == 1:
            state["phase"] = "ask"
            skill = "cafe.order_one"
            message = ("I'm sorry, we don't have " + scenario["wanted"]
                       + " today. What else would you like?")
        elif order and order[1] == scenario["wanted"] and order[0] != 1:
            state["feedback"] = "Вы назвали другое количество. Сравните one (один) и two (два). Попробуйте исправить сами."
        else:
            state["feedback"] = "Не удалось надёжно понять просьбу. Это не оценка ошибки. Попробуйте иначе."
    elif phase == "ask":
        if asks_for_options(answer):
            state["phase"] = "choose"
            skill = "cafe.ask_options"
            available = scenario["available"]
            message = "We have " + available[0] + " and " + available[1] + "."
        else:
            state["feedback"] = "Вы можете уточнить у Мии, какие напитки остались. Ответ не оценён как ошибочный."
    elif phase == "choose":
        if order and order[1] in scenario["available"] and order[0] == 1:
            state["phase"] = "repair"
            state["chosen"] = order[1]
            skill = "cafe.choose"
            message = "Did you say two " + order[1] + "s?"
        elif order and order[0] != 1:
            state["feedback"] = "Здесь нужна одна порция. One — одна, two — две. Попробуйте исправить просьбу."
        else:
            state["feedback"] = "Попросите один из предложенных напитков своими словами; непонятный ответ не оценивается."
    elif phase == "repair":
        if corrects_one(answer, state["chosen"]):
            state["phase"] = "done"
            skill = "cafe.repair"
            message = "Thank you for clarifying! One " + state["chosen"] + ". Here you are."
        else:
            state["feedback"] = "Мия уточняет, не две ли порции. Ответ не подтверждён; попробуйте уточнить количество."
    if skill:
        state["observed"].append(skill)
        state["accepted"].append(answer)
        state["feedback"] = ""
    if message:
        state["messages"].append({"who": "Mia", "text": message})


@login_required
@require_http_methods(["GET", "POST"])
def cafe_mission(request):
    lesson = get_object_or_404(Lesson, slug="a1-cafe-order", is_published=True, level__code="A1")
    state = request.session.get(SESSION_KEY)
    if (not isinstance(state, dict) or state.get("version") != VERSION
            or state.get("owner_id") != request.user.pk):
        state = start_state(request.user.pk)
        # Persist the first GET as well: otherwise the next turn loses the
        # server-owned inventory and the client has no current nonce.
        request.session[SESSION_KEY] = state

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "restart":
            state = start_state(request.user.pk)
        else:
            token = request.POST.get("token", "")
            if not token or not secrets.compare_digest(token, state["nonce"]):
                return HttpResponseBadRequest("Форма устарела. Обновите страницу.")
            if action == "hint" and state["phase"] != "done":
                if state["hints"] < MAX_HINTS:
                    state["hints"] += 1
                    state["feedback"] = HINTS[state["phase"]]
                else:
                    state["feedback"] = "Доступные подсказки уже использованы."
            elif action == "send" and state["phase"] != "done":
                answer = request.POST.get("answer", "").strip()
                if not 2 <= len(answer) <= 80 or state["turns"] >= MAX_TURNS:
                    return HttpResponseBadRequest("Ответ должен содержать 2–80 символов; максимум 9 реплик.")
                state["turns"] += 1
                state["messages"].append({"who": "You", "text": answer})
                advance(state, answer)
            elif action == "save" and state["phase"] == "done":
                # Reject saving an already recorded dialogue, even with the
                # fresh nonce issued after its first successful POST.
                if state.get("saved_id") is not None:
                    return HttpResponseBadRequest("Эта попытка уже сохранена.")
                assistance = request.POST.get("assistance")
                if assistance not in (
                    IndependentAttempt.Assistance.NO_HELP,
                    IndependentAttempt.Assistance.NOTES,
                    IndependentAttempt.Assistance.TRANSLATOR,
                ):
                    return HttpResponseBadRequest("Укажите, использовали ли вы помощь.")
                if state["hints"] and assistance == IndependentAttempt.Assistance.NO_HELP:
                    assistance = IndependentAttempt.Assistance.NOTES
                with transaction.atomic():
                    try:
                        attempt = IndependentAttempt.objects.create(
                            user=request.user, lesson=lesson, skill="transfer",
                            task_variant=200 + state["scenario"],
                            batch_token="cafe-" + state["nonce"],
                            submitted=" / ".join(state["accepted"])[:400],
                            outcome=IndependentAttempt.Outcome.SELF_REPORTED,
                            assistance=assistance,
                            prompt_snapshot=(
                                "Café information gap v1: request one "
                                + SCENARIOS[state["scenario"]]["wanted"]
                                + "; stock unavailable; ask for alternatives; "
                                "request one available drink; correct an intentional "
                                "two-versus-one misunderstanding."
                            ),
                            model_snapshot=(
                                "Criterion: plausible A1 communication; inspect all "
                                "turns and intent, not equality with a model sentence."
                            ),
                            self_rubric={
                                "mission_version": VERSION,
                                "structured_goal_reached": True,
                                "not_language_grade": True,
                                "skill_acts": state["observed"],
                                "hint_count": state["hints"],
                                "transcript": state["messages"],
                            },
                        )
                    except IntegrityError:
                        return HttpResponseBadRequest("Эта попытка уже сохранена.")
                state["saved_id"] = attempt.pk
            else:
                return HttpResponseBadRequest("Недопустимое действие для текущего этапа.")
            # A stale form never replays a previous turn or adds a second attempt.
            state["nonce"] = secrets.token_urlsafe(24)
        request.session[SESSION_KEY] = state
        return redirect("learning:cafe_mission")

    # Server-side inventory / scenario index is intentionally NOT rendered.
    return render(request, "learning/cafe_mission.html", {
        "lesson": lesson, "state": state,
        "can_hint": state["phase"] != "done" and state["hints"] < MAX_HINTS,
        "finished": state["phase"] == "done",
        "skills": SKILLS,
        "wanted": SCENARIOS[state["scenario"]]["wanted"],
    })
