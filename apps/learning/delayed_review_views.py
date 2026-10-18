"""Login-only, server-checked five-question practice after a 48-hour pause."""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.drills.retry_guidance import retry_guidance
from .mistake_review import COUNT, DELAY, due_reviews, variants_for
from .models import MistakeReview


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
                MistakeReview.objects.select_for_update().select_related("exercise__lesson"),
                pk=item_id, user=request.user, completed_at__isnull=True,
                exercise__lesson__is_published=True,
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
                    "reason": retry_guidance(item.exercise, question[2][choice]),
                    "number": index + 1,
                    "finished": finished,
                    "score": score,
                    "rescheduled": rescheduled,
                    "next_due": item.due_at if rescheduled else None,
                }
            }
        return render(request, "learning/mistake_review.html", context)

    item = due_reviews(request.user).first()
    next_due = (MistakeReview.objects.filter(user=request.user, completed_at__isnull=True,
                                             due_at__gt=timezone.now())
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
