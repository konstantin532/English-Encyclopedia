from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.lessons.models import Lesson
from apps.curriculum.models import Week

from django.views.decorators.csrf import ensure_csrf_cookie

from .models import ExerciseAttempt, Status, UnitProgress, WeekGoal
from .services import build_review


@login_required
def dashboard(request):
    progress = UnitProgress.objects.filter(user=request.user).select_related("unit__semantic_class__category")
    now = timezone.now()
    due = [p for p in progress if p.next_review_at and p.next_review_at <= now]
    started = {p.unit_id for p in progress}
    next_lesson = next((l for l in Lesson.objects.filter(is_published=True)
                        if not set(l.units.values_list("id", flat=True)) <= started), None)
    return render(request, "learning/dashboard.html", {
        "progress": progress,
        "new_units": [p for p in progress if p.status != Status.ACTIVE],
        "active_units": [p for p in progress if p.status == Status.ACTIVE],
        "due": due,
        "mistakes": ExerciseAttempt.objects.filter(user=request.user, is_correct=False).select_related("exercise__lesson")[:10],
        "next_lesson": next_lesson,
    })


@login_required
@require_POST
def toggle_markers(request):
    request.user.markers_in_color = not request.user.markers_in_color
    request.user.save(update_fields=["markers_in_color"])
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"color": request.user.markers_in_color})
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
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
