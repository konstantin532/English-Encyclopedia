from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .assignments import complete_assignment, start_assignment, student_assignment
from .models import AssignmentProgress


@login_required
@require_POST
def assignment_open(request, pk):
    progress = start_assignment(request.user, student_assignment(request.user, pk))
    return redirect(f"{reverse('lessons:detail', args=[progress.assignment.lesson.slug])}?assignment={progress.pk}")


@login_required
@require_POST
def assignment_complete(request, pk):
    progress = student_assignment(request.user, pk)
    source = request.POST.get("source")
    if source not in AssignmentProgress.CompletionSource.values:
        return HttpResponseBadRequest("Выберите способ завершения.")
    complete_assignment(
        request.user, progress,
        previously_completed=source == AssignmentProgress.CompletionSource.PREVIOUSLY_COMPLETED,
    )
    messages.success(request, "Отметка сохранена. Это самоотчёт, а не проверка преподавателя.")
    return redirect("learning:dashboard")


@login_required
def assignment_history(request, pk):
    progress = get_object_or_404(
        AssignmentProgress.objects.select_related("assignment__lesson", "assignment__group"),
        pk=pk, student=request.user,
    )
    return render(request, "teaching/assignment_history.html", {
        "progress": progress, "work": progress.work.order_by("-created_at", "-pk"),
    })
