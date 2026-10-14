from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.lessons.models import Lesson

from django.views.decorators.csrf import ensure_csrf_cookie

from .models import ExerciseAttempt, Status, UnitProgress
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
    return redirect(request.POST.get("next") or "learning:dashboard")


@login_required
@ensure_csrf_cookie
def review(request):
    items = build_review(request.user)
    upcoming = (UnitProgress.objects.filter(user=request.user, next_review_at__gt=timezone.now())
                .order_by("next_review_at").first())
    return render(request, "learning/review.html", {"items": items, "upcoming": upcoming})
