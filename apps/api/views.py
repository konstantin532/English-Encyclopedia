import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.drills.models import Exercise, PracticeItem
from apps.drills.retry_guidance import is_open_pilot_response, is_pilot_exercise, retry_guidance
from apps.taxonomy.markup import strip_markup
from apps.learning.services import record_attempt, record_practice, record_recall
from apps.learning.trainer_state import run_serialized
from apps.learning.trainer_service import register_legacy_exposure
from apps.learning.mistake_review import schedule_review
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
        register_legacy_exposure(request.user, exercise.units.all())
        return JsonResponse({"correct": False, "revealed": True, "answer": exercise.answer,
                             "explanation": exercise.explanation_ru})
    answer = payload["answer"]
    open_response = is_open_pilot_response(exercise)
    # Creative transfer has multiple valid formulations. A model-key mismatch
    # must not reduce a learner's stored vocabulary progress as if it were a
    # proven grammatical error.
    unverified = open_response and not exercise.is_correct(answer)
    # The stored answer/progress and its delayed review are one logical operation.
    # If scheduling fails, do not leave an attempted answer without its retry.
    # The shared user gate retries the entire operation on SQLite lock conflicts.
    def record_and_schedule():
        correct = False if unverified else record_attempt(
            request.user, exercise, answer, delay_wrong_days=2 if is_pilot_exercise(exercise) else 0,
        )
        due_at = None
        if not correct and not unverified and is_pilot_exercise(exercise) and request.user.is_authenticated:
            due_at = schedule_review(request.user, exercise)
        return correct, due_at

    correct, due_at = run_serialized(request.user, record_and_schedule)
    data = {"correct": correct, "saved": request.user.is_authenticated and not unverified}
    if due_at:
        data["retry_scheduled_at"] = due_at.isoformat()
        data["retry_count"] = 5
    if open_response:
        data["assessment"] = "needs_review" if unverified else "model_match"
        # An unchecked free reply can be valid. Invite an optional review
        # without storing an incorrect ExerciseAttempt or penalizing progress.
        if unverified:
            data["self_review_available"] = request.user.is_authenticated
    if correct:
        register_legacy_exposure(request.user, exercise.units.all())
        data.update(answer=exercise.answer, explanation=exercise.explanation_ru)
    else:
        guidance = retry_guidance(exercise, answer)
        if guidance:
            data["feedback_ru"] = guidance
    return guest_result(request, data, "exercise", exercise, answer)


@require_POST
def recall_unit(request, uid):
    unit = get_object_or_404(LexicalUnit, uid=uid)
    try:
        payload = read_answer_payload(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    explanation = f"{unit.lemma} {unit.ipa_us} — {unit.translation_ru}. Пример: {strip_markup(unit.example_en)}"
    if payload.get("reveal"):
        register_legacy_exposure(request.user, [unit])
        return JsonResponse({"correct": False, "revealed": True, "answer": unit.lemma, "explanation": explanation})
    answer = payload["answer"]
    correct = record_recall(request.user, unit, answer)
    data = {"correct": correct, "saved": request.user.is_authenticated}
    if correct:
        register_legacy_exposure(request.user, [unit])
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


@require_POST
def check_practice(request, pk):
    """Перевод с русского. Совпадение со списком — верно; несовпадение не объявляется ошибкой:
    одну мысль можно сказать по-разному, поэтому ученик сравнивает свой вариант с образцом."""
    item = get_object_or_404(PracticeItem.objects.select_related("lesson"), pk=pk, lesson__is_published=True)
    try:
        payload = read_answer_payload(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    if payload.get("reveal"):
        register_legacy_exposure(request.user, item.units.all())
        return JsonResponse({"correct": False, "revealed": True, "answer": item.answer,
                             "explanation": item.explanation_ru})
    if item.is_correct(payload["answer"]):
        record_practice(request.user, item)
        register_legacy_exposure(request.user, item.units.all())
        return guest_result(request, {"correct": True, "saved": request.user.is_authenticated,
                             "assessment": "model_match", "answer": item.answer,
                             "explanation": item.explanation_ru}, "practice", item, payload["answer"])
    data = {"correct": False, "saved": False, "assessment": "needs_review",
            "self_review_available": request.user.is_authenticated}
    if item.hint_ru:
        data["feedback_ru"] = item.hint_ru
    return JsonResponse(data)


def guest_result(request, data, kind, item, answer):
    if not request.user.is_authenticated:
        from apps.learning.guest_progress import make_receipt
        receipt = make_receipt(kind, item, answer)
        if receipt:
            data['guest_receipt'] = receipt
    return JsonResponse(data)


@login_required
@require_POST
def import_guest_progress(request):
    from apps.learning.guest_progress import import_results, MAX_ITEMS
    if len(request.body) > MAX_ITEMS * 4200:
        return JsonResponse({'error': 'Слишком много результатов.'}, status=400)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError('Некорректные результаты.')
        result = import_results(request.user, payload.get('receipts'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Некорректные результаты.'}, status=400)
    return JsonResponse(result)


@require_POST
def guest_week_goal(request, pk):
    from apps.curriculum.models import Week
    from apps.learning.guest_progress import make_goal_receipt
    week = get_object_or_404(Week.objects.select_related('level'), pk=pk, number=1, level__code='A1')
    status = request.POST.get('status')
    receipt = make_goal_receipt(week, status)
    if not receipt:
        return JsonResponse({'error': 'Выберите отметку.'}, status=400)
    return JsonResponse({'guest_receipt': receipt, 'status': status, 'saved': False})
