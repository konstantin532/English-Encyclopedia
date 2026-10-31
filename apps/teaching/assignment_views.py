from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.lessons.models import Lesson

from .access import teacher_required
from .assignments import (complete_assignment, create_lesson_assignment, start_assignment, student_assignment,
                          overdue_for_teacher, teacher_assignment_progress, teacher_assignments)
from .models import AssignmentProgress, LessonAssignment, StudyGroup
from .review import reviewable


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


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = LessonAssignment
        fields = ["group", "lesson", "due_date"]
        labels = {"group": "Группа", "lesson": "Опубликованный урок", "due_date": "Срок (необязательно, Москва)"}
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, teacher, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["group"].queryset = StudyGroup.objects.filter(teacher=teacher)
        self.fields["lesson"].queryset = Lesson.objects.filter(is_published=True).select_related(
            "level",
        ).order_by("level__order", "order")


@teacher_required
def assignment_new(request):
    form = AssignmentForm(request.POST or None, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        assignment = create_lesson_assignment(teacher=request.user, **form.cleaned_data)
        messages.success(request, "Урок назначен текущим участникам группы.")
        return redirect("teaching:assignment", pk=assignment.pk)
    return render(request, "teaching/assignment_form.html", {"form": form})


@teacher_required
def assignment_list(request):
    page = Paginator(teacher_assignments(request.user), 25).get_page(request.GET.get("page"))
    return render(request, "teaching/assignments.html", {"page": page})


@teacher_required
def overdue_list(request):
    page = Paginator(overdue_for_teacher(request.user), 20).get_page(request.GET.get("page"))
    return render(request, "teaching/overdue_assignments.html", {"page": page})


@teacher_required
def assignment_detail(request, pk):
    assignment = get_object_or_404(teacher_assignments(request.user), pk=pk)
    records = teacher_assignment_progress(request.user).filter(assignment=assignment).prefetch_related(
        Prefetch("work", queryset=reviewable(request.user).order_by("-created_at"), to_attr="visible_work"),
    ).order_by("student__display_name", "student_id")
    return render(request, "teaching/assignment_detail.html", {
        "assignment": assignment, "records": records,
    })
