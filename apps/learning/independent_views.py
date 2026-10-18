"""Four deliberately separate beginner checks, submitted blind as one session.

No multiple choice, no answer keys before a submission, and no false claim
that matching a model proves independent communicative proficiency.
"""
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from apps.lessons.models import Lesson
from .models import IndependentAttempt
from .understanding import get_guide, model_agreement

RATINGS = {
    "independent": "Смог выразить мысль самостоятельно",
    "helped": "Понадобилась подсказка или образец",
    "not_yet": "Пока трудно, хочу вернуться к этому",
}
TASKS = ("meaning", "writing", "transfer", "explain")


@login_required
@require_http_methods(["GET", "POST"])
def independent_check(request, slug):
    lesson = get_object_or_404(Lesson.objects.select_related("level"),
                               slug=slug, level__code="A1", is_published=True)
    guide = get_guide(lesson.slug)
    if guide is None:
        return HttpResponseBadRequest("Самостоятельная проверка для урока ещё не подготовлена.")

    result = None
    batch_results = None
    if request.method == "POST":
        if request.POST.get("action") == "rate":
            try:
                attempt_id = int(request.POST.get("attempt_id", ""))
            except (TypeError, ValueError):
                return HttpResponseBadRequest("Некорректный номер попытки.")
            rating = request.POST.get("rating")
            if rating not in RATINGS:
                return HttpResponseBadRequest("Выберите один из трёх вариантов.")
            attempt = get_object_or_404(
                IndependentAttempt, pk=attempt_id, user=request.user,
                lesson=lesson, skill__in=("transfer", "explain"),
                outcome=IndependentAttempt.Outcome.SELF_REPORTED,
            )
            attempt.self_rating = rating
            attempt.save(update_fields=["self_rating"])
            result = {"skill": attempt.skill, "model": guide["tasks"][attempt.skill]["model"],
                      "label": RATINGS[rating], "attempt": attempt}
        elif request.POST.get("action") == "batch":
            # Crucially, do not reveal ANY answer until the learner has
            # submitted ALL FOUR responses; this prevents the first revealed
            # example from contaminating the remaining unaided answers.
            answers = {key: request.POST.get("answer_" + key, "") for key in TASKS}
            if any(not isinstance(value, str) or not value.strip()
                   or len(value) > 400 for value in answers.values()):
                return HttpResponseBadRequest(
                    "Сначала ответьте на все четыре вопроса (до 400 символов каждый)."
                )
            batch_results = []
            with transaction.atomic():
                for skill in TASKS:
                    answer = answers[skill].strip()
                    open_response = skill in ("transfer", "explain")
                    matches = not open_response and model_agreement(
                        guide["tasks"][skill], answer)
                    outcome = (
                        IndependentAttempt.Outcome.SELF_REPORTED if open_response
                        else IndependentAttempt.Outcome.MODEL_MATCH if matches
                        else IndependentAttempt.Outcome.NEEDS_REVIEW
                    )
                    attempt = IndependentAttempt.objects.create(
                        user=request.user, lesson=lesson,
                        skill=skill, submitted=answer, outcome=outcome,
                    )
                    batch_results.append({
                        "skill": skill, "title": {
                            "meaning": "Понимание смысла",
                            "writing": "Самостоятельное письмо",
                            "transfer": "Применение в новой ситуации",
                            "explain": "Объяснение правила",
                        }[skill], "attempt": attempt,
                        "model": guide["tasks"][skill]["model"],
                        "label": (
                            "Свободный ответ: сравните смысл и оцените себя сами."
                            if open_response
                            else "Совпало с образцом; это ещё не доказательство владения."
                            if matches else
                            "Не совпало с образцом — это не обязательно ошибка."
                        ),
                    })
        else:
            skill = request.POST.get("skill")
            if skill not in TASKS:
                return HttpResponseBadRequest("Неизвестный вид задания.")
            answer = request.POST.get("answer", "")
            if not isinstance(answer, str) or not answer.strip() or len(answer) > 400:
                return HttpResponseBadRequest("Напишите ответ длиной до 400 символов.")
            # The open transfer response has no exhaustive answer key.
            is_open = skill in ("transfer", "explain")
            matches = not is_open and model_agreement(guide["tasks"][skill], answer)
            outcome = (IndependentAttempt.Outcome.SELF_REPORTED if is_open else
                       IndependentAttempt.Outcome.MODEL_MATCH if matches else
                       IndependentAttempt.Outcome.NEEDS_REVIEW)
            attempt = IndependentAttempt.objects.create(
                user=request.user, lesson=lesson, skill=skill,
                submitted=answer.strip(), outcome=outcome,
            )
            label = ("Творческий ответ сохранён для самооценки; система не объявляет его верным или неверным."
                     if is_open else
                     "Ответ совпал с подготовленным образцом, но это ещё не сертификат владения языком."
                     if matches else
                     "Ответ отличается от образца. Он может быть допустимым — проверьте вручную.")
            result = {"skill": skill, "model": guide["tasks"][skill]["model"],
                      "label": label, "attempt": attempt}
    attempts = (IndependentAttempt.objects.filter(user=request.user, lesson=lesson)
                .order_by("-created_at")[:12])
    return render(request, "learning/independent_check.html", {
        "lesson": lesson, "guide": guide, "tasks": [
            {"key": key, "item": guide["tasks"][key],
             "title": {"meaning": "1. Понимаю смысл", "writing": "2. Пишу сам",
                       "transfer": "3. Переношу в новую ситуацию",
                       "explain": "4. Объясняю почему"}[key]}
            for key in TASKS],
        "result": result, "batch_results": batch_results,
        "ratings": RATINGS, "attempts": attempts,
    })
