"""Human verification of free A1 answers; no automated CEFR claims."""
from django import forms
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .understanding import get_guide
from .models import IndependentAttempt


SCALE = (
    ("", "— Выберите —"),
    ("yes", "Да: выполняет критерий"),
    ("partly", "Частично: есть неточность"),
    ("not_yet", "Нет: нужна доработка"),
)


class IndependentAttemptReviewForm(forms.ModelForm):
    rubric_meaning = forms.ChoiceField(
        label="Передаёт смысл задания?", choices=SCALE, required=False,
    )
    rubric_form = forms.ChoiceField(
        label="Грамматическая форма и порядок слов?", choices=SCALE, required=False,
    )
    rubric_context = forms.ChoiceField(
        label="Естественно и уместно в ситуации?", choices=SCALE, required=False,
    )

    class Meta:
        model = IndependentAttempt
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        rubric = self.instance.teacher_rubric or {}
        for axis in ("meaning", "form", "context"):
            self.fields["rubric_" + axis].initial = rubric.get(axis, "")

    def clean(self):
        data = super().clean()
        verdict = data.get("teacher_verdict")
        axes = [data.get("rubric_" + axis) for axis in ("meaning", "form", "context")]
        if verdict and verdict != IndependentAttempt.TeacherVerdict.UNREVIEWED:
            if not IndependentAttemptAdmin._task(self.instance):
                raise forms.ValidationError(
                    "Невозможно восстановить исходное задание: заключение запрещено.")
            if any(value not in ("yes", "partly", "not_yet") for value in axes):
                raise forms.ValidationError("Заполните смысл, грамматику и уместность.")
            if len((data.get("teacher_note") or "").strip()) < 20:
                raise forms.ValidationError(
                    "Обоснуйте заключение конкретной подсказкой (от 20 символов).")
            if verdict == IndependentAttempt.TeacherVerdict.MEETS_TASK and any(
                    value != "yes" for value in axes):
                raise forms.ValidationError(
                    "Для «соответствует задаче» все три критерия должны быть «Да».")
        return data


@admin.register(IndependentAttempt)
class IndependentAttemptAdmin(admin.ModelAdmin):
    form = IndependentAttemptReviewForm
    list_display = ("created_at", "lesson", "user", "skill",
                    "outcome", "teacher_verdict", "reviewed_at")
    list_filter = ("skill", "outcome", "teacher_verdict")
    search_fields = ("user__email", "lesson__title", "submitted")
    readonly_fields = (
        "user", "lesson", "skill", "task_variant", "submitted", "outcome",
        "self_rating", "self_rubric", "teacher_rubric",
        "reviewed_by", "reviewed_at", "created_at",
        "original_prompt", "reference_example",
    )
    fields = (
        "user", "lesson", "skill", "task_variant", "original_prompt",
        "submitted", "reference_example", "outcome",
        "self_rating", "self_rubric", "created_at", "teacher_verdict",
        "rubric_meaning", "rubric_form", "rubric_context",
        "teacher_note", "teacher_rubric", "reviewed_by", "reviewed_at",
    )

    @admin.display(description="Исходная ситуация ученика")
    def original_prompt(self, obj):
        task = self._task(obj)
        if not task:
            return "Не удалось найти задание для этой версии. Не оценивайте вслепую."
        return format_html('<p lang="ru" style="white-space:pre-wrap">{}</p>', task["prompt"])

    @admin.display(description="Один возможный образец (не единственный)")
    def reference_example(self, obj):
        task = self._task(obj)
        if not task:
            return "Образец отсутствует: нужна ручная проверка содержания."
        return format_html('<p style="white-space:pre-wrap">{}</p>', task["model"])

    @staticmethod
    def _task(obj):
        if not obj or not obj.pk:
            return None
        guide = get_guide(obj.lesson.slug)
        if not guide:
            return None
        if obj.skill == "transfer":
            choices = (guide["tasks"]["transfer"], *guide.get("transfer_variants", []))
            if not 0 <= obj.task_variant < len(choices):
                return None
            return choices[obj.task_variant]
        return guide["tasks"].get(obj.skill)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if obj.teacher_verdict == IndependentAttempt.TeacherVerdict.UNREVIEWED:
            obj.teacher_rubric = {}
            obj.reviewed_by = None
            obj.reviewed_at = None
        else:
            obj.teacher_rubric = {
                axis: form.cleaned_data["rubric_" + axis]
                for axis in ("meaning", "form", "context")
            }
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)
