import json

from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.drills.models import Exercise
from apps.taxonomy.markup import strip_markup
from apps.learning.services import record_attempt, record_recall
from apps.lexicon.models import LexicalUnit
from apps.poems.models import Poem


def _parse_json_object(request):
    """Отвергает некорректный JSON и значения, отличные от объекта."""
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


@require_POST
def check_exercise(request, pk):
    exercise = get_object_or_404(Exercise.objects.select_related("lesson"), pk=pk, lesson__is_published=True)
    payload = _parse_json_object(request)
    if payload is None:
        return HttpResponseBadRequest("Неверный JSON: ожидается объект")
    if payload.get("reveal"):
        return JsonResponse({"correct": False, "revealed": True, "answer": exercise.answer,
                             "explanation": exercise.explanation_ru})
    answer = str(payload.get("answer", "")).strip()
    if not answer:
        return JsonResponse({"error": "Введите ответ"}, status=400)
    correct = record_attempt(request.user, exercise, answer)
    data = {"correct": correct, "saved": request.user.is_authenticated}
    if correct:
        data.update(answer=exercise.answer, explanation=exercise.explanation_ru)
    return JsonResponse(data)


@require_POST
def recall_unit(request, uid):
    unit = get_object_or_404(LexicalUnit, uid=uid)
    payload = _parse_json_object(request)
    if payload is None:
        return HttpResponseBadRequest("Неверный JSON: ожидается объект")
    explanation = f"{unit.lemma} {unit.ipa_us} — {unit.translation_ru}. Пример: {strip_markup(unit.example_en)}"
    if payload.get("reveal"):
        return JsonResponse({"correct": False, "revealed": True, "answer": unit.lemma, "explanation": explanation})
    answer = str(payload.get("answer", "")).strip()
    if not answer:
        return JsonResponse({"error": "Введите ответ"}, status=400)
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
    payload = _parse_json_object(request)
    if payload is None:
        return HttpResponseBadRequest("Неверный JSON: ожидается объект")
    word = poem.gaps[index]["word"]
    if payload.get("reveal"):
        return JsonResponse({"correct": False, "answer": word})
    correct = Exercise.normalize(str(payload.get("answer", ""))) == Exercise.normalize(word)
    return JsonResponse({"correct": correct, **({"answer": word} if correct else {})})
