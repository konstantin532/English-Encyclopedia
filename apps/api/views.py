from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.drills.models import Exercise
from apps.drills.retry_guidance import is_open_pilot_response, retry_guidance
from apps.taxonomy.markup import strip_markup
from apps.learning.services import record_attempt, record_recall
from apps.lexicon.models import LexicalUnit
from apps.poems.models import Poem

from .validation import read_answer_payload


@require_POST
def check_exercise(request, pk):
    exercise = get_object_or_404(Exercise.objects.select_related("lesson"), pk=pk, lesson__is_published=True)
    try:
        payload = read_answer_payload(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    if payload.get("reveal"):
        return JsonResponse({"correct": False, "revealed": True, "answer": exercise.answer,
                             "explanation": exercise.explanation_ru})
    answer = payload["answer"]
    open_response = is_open_pilot_response(exercise)
    # Creative transfer has multiple valid formulations. A model-key mismatch
    # must not reduce a learner's stored vocabulary progress as if it were a
    # proven grammatical error.
    unverified = open_response and not exercise.is_correct(answer)
    correct = False if unverified else record_attempt(request.user, exercise, answer)
    data = {"correct": correct, "saved": request.user.is_authenticated and not unverified}
    if open_response:
        data["assessment"] = "needs_review" if unverified else "model_match"
    if correct:
        data.update(answer=exercise.answer, explanation=exercise.explanation_ru)
    else:
        guidance = retry_guidance(exercise, answer)
        if guidance:
            data["feedback_ru"] = guidance
    return JsonResponse(data)


@require_POST
def recall_unit(request, uid):
    unit = get_object_or_404(LexicalUnit, uid=uid)
    try:
        payload = read_answer_payload(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    explanation = f"{unit.lemma} {unit.ipa_us} — {unit.translation_ru}. Пример: {strip_markup(unit.example_en)}"
    if payload.get("reveal"):
        return JsonResponse({"correct": False, "revealed": True, "answer": unit.lemma, "explanation": explanation})
    answer = payload["answer"]
    correct = record_recall(request.user, unit, answer)
    data = {"correct": correct, "saved": request.user.is_authenticated}
    if correct:
        data.update(answer=unit.lemma, explanation=explanation)
    return JsonResponse(data)


@require_POST
def check_poem_gap(request, number, index):
    poem = get_object_or_404(Poem, number=number, is_published=True)
    if index >= len(poem.gaps):
        return JsonResponse({"error": "Нет такого пропуска"}, status=404)
    try:
        payload = read_answer_payload(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    word = poem.gaps[index]["word"]
    if payload.get("reveal"):
        return JsonResponse({"correct": False, "answer": word})
    correct = Exercise.normalize(payload["answer"]) == Exercise.normalize(word)
    return JsonResponse({"correct": correct, **({"answer": word} if correct else {})})
