from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from urllib.parse import quote

from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.views.decorators.http import require_POST

from datetime import timedelta

from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .access import can_teach, teacher_required, visible_students
from .models import ContentDraft, CourseIssue, GroupMembership, StudyGroup
from .progress import recent_attempts, summarize, week_goals
from .review import DraftForm, IssueForm, TeacherReviewForm, review_queue, reviewable, save_review, task_for

ISSUES_PER_DAY = 20


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


@teacher_required
def review_list(request):
    queue = list(review_queue(request.user)[:100])
    return render(request, "teaching/review_list.html", {"queue": queue})


@teacher_required
def review_detail(request, pk):
    attempt = get_object_or_404(reviewable(request.user), pk=pk)
    task = task_for(attempt)
    form = TeacherReviewForm(request.POST or None, instance=attempt)
    if request.method == "POST" and form.is_valid():
        save_review(form, request.user)
        messages.success(request, "Проверка сохранена. Ученик увидит заключение и подсказку.")
        nxt = review_queue(request.user).exclude(pk=attempt.pk).first()
        return redirect("teaching:review", pk=nxt.pk) if nxt else redirect("teaching:review_list")
    return render(request, "teaching/review_detail.html", {"attempt": attempt, "task": task, "form": form})


def _safe_page(request, value: str) -> str:
    value = (value or "").strip()[:300]
    if value.startswith("/") and not value.startswith("//") and url_has_allowed_host_and_scheme(
            value, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return value
    return ""


@login_required
def report_issue(request):
    """Ученик или учитель сообщает об ошибке в материалах курса."""
    page = _safe_page(request, request.POST.get("page") or request.GET.get("page"))
    form = IssueForm(request.POST or None, initial={"quote": request.GET.get("quote", "")[:300]})
    if request.method == "POST" and form.is_valid():
        recent = CourseIssue.objects.filter(reporter=request.user,
                                            created_at__gte=timezone.now() - timedelta(days=1)).count()
        if recent >= ISSUES_PER_DAY:
            form.add_error(None, "Сегодня вы уже отправили много сообщений. Спасибо! Продолжите завтра.")
        elif not page:
            form.add_error(None, "Не удалось понять, о какой странице речь. Откройте сообщение со страницы с ошибкой.")
        else:
            CourseIssue.objects.create(reporter=request.user, reporter_is_teacher=can_teach(request.user),
                                       page=page, quote=form.cleaned_data["quote"], comment=form.cleaned_data["comment"])
            return redirect(f"{resolve_url('teaching:report_issue')}?sent=1&page={quote(page)}")
    mine = CourseIssue.objects.filter(reporter=request.user)[:10]
    return render(request, "teaching/report_issue.html", {"form": form, "page": page, "mine": mine,
                                                           "sent": request.GET.get("sent") == "1"})


MAX_OPEN_DRAFTS = 30


@teacher_required
def draft_list(request):
    drafts = ContentDraft.objects.filter(author=request.user)
    return render(request, "teaching/draft_list.html", {"drafts": drafts})


@teacher_required
def draft_edit(request, pk=None):
    # Только свои черновики; чужой — 404. Отправленный на проверку не редактируется.
    draft = get_object_or_404(ContentDraft, pk=pk, author=request.user) if pk else None
    if draft and not draft.editable:
        messages.info(request, "Черновик на проверке или уже одобрен — изменить его нельзя.")
        return redirect("teaching:drafts")
    if draft is None and request.method == "POST" and ContentDraft.objects.filter(
            author=request.user, status__in=ContentDraft.EDITABLE).count() >= MAX_OPEN_DRAFTS:
        messages.info(request, "Слишком много незавершённых черновиков. Отправьте или удалите часть.")
        return redirect("teaching:drafts")
    form = DraftForm(request.POST or None, instance=draft)
    if request.method == "POST" and form.is_valid():
        draft = form.save(commit=False)
        draft.author = request.user
        submit = "submit" in request.POST
        if submit:
            draft.status, draft.submitted_at = ContentDraft.Status.SUBMITTED, timezone.now()
        else:
            draft.status = ContentDraft.Status.DRAFT
        draft.save()
        messages.success(request, "Отправлено автору курса." if submit else "Черновик сохранён.")
        return redirect("teaching:drafts")
    return render(request, "teaching/draft_edit.html", {"form": form, "draft": draft})


@teacher_required
@require_POST
def draft_delete(request, pk):
    draft = get_object_or_404(ContentDraft, pk=pk, author=request.user)
    if draft.editable:
        draft.delete()
        messages.success(request, "Черновик удалён.")
    return redirect("teaching:drafts")
