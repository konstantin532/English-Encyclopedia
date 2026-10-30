from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .access import can_teach, teacher_required, visible_students
from .models import GroupMembership, StudyGroup
from .progress import recent_attempts, summarize, week_goals


def for_teachers(request):
    """Открытая страница: что умеет кабинет учителя и как в него попасть."""
    return render(request, "teaching/for_teachers.html", {"can_teach": can_teach(request.user)})


class GroupForm(forms.ModelForm):
    class Meta:
        model = StudyGroup
        fields = ["name"]
        labels = {"name": "Название группы"}


@teacher_required
def dashboard(request):
    form = GroupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        group = form.save(commit=False)
        group.teacher = request.user
        group.save()
        messages.success(request, f"Группа «{group.name}» создана. Код для учеников: {group.join_code}")
        return redirect("teaching:dashboard")
    groups = StudyGroup.objects.filter(teacher=request.user).prefetch_related("memberships")
    return render(request, "teaching/dashboard.html", {
        "groups": groups, "form": form,
        "student_count": visible_students(request.user).count(),
        "sees_all": request.user.is_superuser or request.user.teacher_sees_all,
    })


@teacher_required
def students(request):
    rows = [(s, summarize(s)) for s in visible_students(request.user)
            .select_related("current_level", "group_membership__group").order_by("display_name", "email")]
    return render(request, "teaching/students.html", {
        "rows": rows, "sees_all": request.user.is_superuser or request.user.teacher_sees_all,
    })


@teacher_required
def student_detail(request, pk):
    # 404, а не 403: учитель не узнаёт даже о существовании чужого ученика.
    student = get_object_or_404(visible_students(request.user).select_related("current_level"), pk=pk)
    return render(request, "teaching/student_detail.html", {
        "student": student, "summary": summarize(student),
        "attempts": recent_attempts(student), "goals": week_goals(student),
        "membership": GroupMembership.objects.filter(student=student).select_related("group").first(),
    })


class JoinForm(forms.Form):
    code = forms.CharField(label="Код группы", max_length=12)

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper().replace(" ", "").replace("-", "")


@login_required
def join_group(request):
    """Ученик вступает в группу по коду от учителя (одна группа за раз)."""
    membership = GroupMembership.objects.filter(student=request.user).select_related("group__teacher").first()
    form = JoinForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not request.user.is_learner:
            form.add_error(None, "В группу вступают только ученики.")
        else:
            group = StudyGroup.objects.filter(join_code=form.cleaned_data["code"], is_open=True).first()
            if group is None:
                form.add_error("code", "Такой группы нет или она закрыта для новых учеников. Проверьте код у учителя.")
            else:
                try:
                    with transaction.atomic():
                        GroupMembership.objects.update_or_create(student=request.user, defaults={"group": group})
                except IntegrityError:
                    form.add_error(None, "Не получилось вступить. Попробуйте ещё раз.")
                else:
                    messages.success(request, f"Вы в группе «{group.name}».")
                    return redirect("teaching:join")
    return render(request, "teaching/join.html", {"form": form, "membership": membership})


@login_required
@require_POST
def leave_group(request):
    GroupMembership.objects.filter(student=request.user).delete()
    messages.success(request, "Вы вышли из группы.")
    return redirect("teaching:join")
