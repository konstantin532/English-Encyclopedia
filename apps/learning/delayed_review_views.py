"""Login-only, server-checked five-question practice after a 48-hour pause."""
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.drills.models import Exercise
from apps.drills.retry_guidance import is_open_pilot_response
from .mistake_review import COUNT, DELAY, available_reviews, due_reviews, variants_for, schedule_review


@login_required
@require_http_methods(["GET", "POST"])
def mistake_review(request):
    if request.method == "POST":
        try:
            item_id = int(request.POST.get("review_id", ""))
            index = int(request.POST.get("index", ""))
            choice = int(request.POST.get("choice", ""))
        except (ValueError, TypeError):
            return HttpResponseBadRequest("Выберите ответ на текущее задание.")
        with transaction.atomic():
            item = get_object_or_404(
                available_reviews(request.user).select_for_update().select_related("exercise__lesson"),
                pk=item_id,
            )
            now = timezone.now()
            if item.due_at > now or item.current_index != index:
                return HttpResponseBadRequest("Это задание ещё не доступно или уже проверено.")
            variants = variants_for(item.exercise)
            if len(variants) != COUNT or not (0 <= index < COUNT) or choice not in (0, 1, 2):
                return HttpResponseBadRequest("Некорректный вариант ответа.")
            question = variants[index]
            right = question[3]
            correct = choice == right
            item.correct_count += int(correct)
            item.current_index += 1
            finished = item.current_index == COUNT
            score = item.correct_count
            rescheduled = False
            if finished:
                if score == COUNT:
                    item.completed_at = now
                else:
                    # Missed concepts reappear in two days, never immediately.
                    item.due_at = now + DELAY
                    item.current_index = 0
                    item.correct_count = 0
                    rescheduled = True
            item.save()
            context = {
                "answer_result": {
                    "correct": correct,
                    "chosen": question[2][choice],
                    "model": question[2][right],
                    # A delayed question checks its *own* sentence, not
                    # necessarily the exact error in the original exercise.
                    # Never display the original hint as if it explained an
                    # unrelated alternative question.
                    "reason": question[4] if len(question) > 4 else (
                        "Сравните варианты и обратите внимание на порядок слов, "
                        "форму глагола и смысл ситуации." if not correct else ""
                    ),
                    "number": index + 1,
                    "finished": finished,
                    "score": score,
                    "rescheduled": rescheduled,
                    "next_due": item.due_at if rescheduled else None,
                }
            }
        return render(request, "learning/mistake_review.html", context)

    item = due_reviews(request.user).first()
    next_due = (available_reviews(request.user).filter(due_at__gt=timezone.now())
                .order_by("due_at").first())
    context = {"next_due": next_due}
    if item:
        variants = variants_for(item.exercise)
        if len(variants) == COUNT and 0 <= item.current_index < COUNT:
            row = variants[item.current_index]
            context["task"] = {
                "id": item.pk,
                "index": item.current_index,
                "number": item.current_index + 1,
                "lesson_title": item.exercise.lesson.title,
                "prompt_ru": row[0],
                "prompt_en": row[1],
                "options": list(enumerate(row[2])),
            }
    return render(request, "learning/mistake_review.html", context)



@login_required
@require_POST
def request_optional_review(request, exercise_id):
    """Explicit learner opt-in for an open transfer answer; NEVER grade it as wrong."""
    exercise = get_object_or_404(
        Exercise.objects.select_related("lesson__level"),
        pk=exercise_id, lesson__is_published=True,
    )
    if not is_open_pilot_response(exercise) or not variants_for(exercise):
        return HttpResponseBadRequest("Для этого задания нет добровольного повторения.")
    due_at = schedule_review(request.user, exercise)
    return JsonResponse({"scheduled": True, "due_at": due_at.isoformat(), "count": COUNT,
                         "note": "Добровольная практика не считается исправлением подтверждённой ошибки."})


@login_required
@require_POST
def request_practice_review(request, item_id):
    """Ученик сам просит пять вопросов на тему перевода через 2 дня. Это не штраф за ошибку."""
    from apps.drills.models import PracticeItem

    item = get_object_or_404(PracticeItem.objects.select_related("lesson"), pk=item_id, lesson__is_published=True)
    exercise = item.lesson.exercises.filter(order=item.review_of).first()
    if exercise is None or not variants_for(exercise):
        return HttpResponseBadRequest("Для этого перевода нет добровольного повторения.")
    due_at = schedule_review(request.user, exercise)
    return JsonResponse({"scheduled": True, "due_at": due_at.isoformat(), "count": COUNT,
                         "note": "Добровольная практика не считается исправлением подтверждённой ошибки."})
