"""Страница тренировки фраз. Выключена, пока EE_PHRASE_MEMORY_ENABLED=False.

POST → redirect → GET: обновление страницы не отправляет ответ повторно,
а повтор того же POST ничего не меняет (проверка по id задания).
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from . import memory, phrase_practice


def phrase_endpoint(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not memory.enabled():
            response = HttpResponseNotFound("Тренировка фраз пока недоступна.")
        else:
            response = login_required(view)(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        response["Vary"] = "Cookie"
        return response
    return wrapped


@phrase_endpoint
@require_http_methods(["GET", "POST"])
def phrase_practice_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action in ("check", "dont_know"):
            text = "" if action == "dont_know" else request.POST.get("answer", "")[:300]
            phrase_practice.answer(request, request.POST.get("item", ""), text)
        elif action == "next":
            phrase_practice.advance(request)
        elif action == "more":
            phrase_practice.continue_rounds(request)
        elif action == "stop":
            phrase_practice.stop_for_today(request)
        return redirect("learning:phrases")
    state = phrase_practice.current(request)
    item = state.get("item")
    changes = []
    if item and item.get("result"):
        for ch in item["result"].get("changes", []):
            changes.append({"lemma": ch["lemma"], "before": memory.stage_name(ch["before"]),
                            "after": memory.stage_name(ch["after"])})
    context = {
        "state": state, "item": item, "changes": changes,
        "summary": phrase_practice.summary(request.user),
        "started": state.get("pos") is not None,
        "done": state.get("correct", 0) + state.get("errors", 0),
        "correct_total": (total := phrase_practice.correct_total(request.user)),
        "puzzle_percent": memory.puzzle_percent(total),
        "round": phrase_practice.round_info(state),
    }
    return render(request, "learning/phrases.html", context)
