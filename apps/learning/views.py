from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.lessons.models import Lesson
from apps.curriculum.models import Week

from django.views.decorators.csrf import ensure_csrf_cookie

from .models import ExerciseAttempt, Status, UnitProgress, WeekGoal, IndependentAttempt
from .mistake_review import available_reviews
from .speech_practice import valid_due_speech_items
from .services import build_review


@login_required
def dashboard(request):
    progress = UnitProgress.objects.filter(user=request.user).select_related("unit__semantic_class__category")
    now = timezone.now()
    due = [p for p in progress if p.next_review_at and p.next_review_at <= now]
    started = {p.unit_id for p in progress}
    lessons = Lesson.objects.filter(is_published=True).prefetch_related("units")
    next_lesson = next((lesson for lesson in lessons
                        if any(unit.pk not in started for unit in lesson.units.all())), None)
    return render(request, "learning/dashboard.html", {
        "progress": progress,
        "new_units": [p for p in progress if p.status != Status.ACTIVE],
        "active_units": [p for p in progress if p.status == Status.ACTIVE],
        "due": due,
        "mistakes": ExerciseAttempt.objects.filter(user=request.user, is_correct=False).select_related("exercise__lesson")[:10],
        "next_lesson": next_lesson,
        "speech_due_count": sum(1 for _ in valid_due_speech_items(request.user, now=now)),
        "independent_attempt_count": IndependentAttempt.objects.filter(user=request.user).count(),
        "independent_lessons_tried": (IndependentAttempt.objects.filter(user=request.user)
                                       .values("lesson_id").distinct().count()),
        "mistake_review_due_count": available_reviews(request.user).filter(due_at__lte=now).count(),
        "mistake_review_waiting": available_reviews(request.user).filter(
            due_at__gt=now).order_by("due_at").first(),
    })


@login_required
@require_POST
def toggle_markers(request):
    request.user.markers_in_color = not request.user.markers_in_color
    request.user.save(update_fields=["markers_in_color"])
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"color": request.user.markers_in_color})
    destination = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(destination, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return HttpResponseRedirect(destination)
    return redirect("learning:dashboard")


@login_required
@ensure_csrf_cookie
def review(request):
    items = build_review(request.user)
    upcoming = (UnitProgress.objects.filter(user=request.user, next_review_at__gt=timezone.now())
                .order_by("next_review_at").first())
    return render(request, "learning/review.html", {"items": items, "upcoming": upcoming})


@login_required
@require_POST
def week_goal(request, week_id):
    week = get_object_or_404(Week.objects.select_related("level"), pk=week_id)
    status = request.POST.get("status")
    if status not in WeekGoal.GoalStatus.values:
        return HttpResponseBadRequest("Выберите «Получилось» или «Ещё нет».")
    WeekGoal.objects.update_or_create(user=request.user, week=week, defaults={"status": status})
    return redirect("curriculum:week", slug=week.level.slug, number=week.number)
