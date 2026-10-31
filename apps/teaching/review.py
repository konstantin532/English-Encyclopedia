"""Проверка свободных ответов учителем. Те же правила, что в админке (apps/learning/admin.py)."""
from django import forms
from django.db.models import F, Q
from django.utils import timezone

from apps.learning.admin import IndependentAttemptAdmin, IndependentAttemptReviewForm
from apps.learning.models import IndependentAttempt

from .access import visible_students
from .models import ContentDraft

NEEDS_HUMAN = (IndependentAttempt.Outcome.NEEDS_REVIEW, IndependentAttempt.Outcome.SELF_REPORTED)


def review_queue(teacher):
    """Непроверенные свободные ответы видимых учителю учеников, старые сверху."""
    return (reviewable(teacher)
            .filter(outcome__in=NEEDS_HUMAN,
                    teacher_verdict=IndependentAttempt.TeacherVerdict.UNREVIEWED)
            .select_related("user", "lesson").order_by("created_at"))


def reviewable(teacher):
    records = IndependentAttempt.objects.filter(user__in=visible_students(teacher))
    if not (teacher.is_superuser or teacher.teacher_sees_all):
        records = records.filter(
            Q(assignment_progress__isnull=True)
            | Q(assignment_progress__withdrawn_at__isnull=True,
                assignment_progress__assignment__group__teacher=teacher,
                assignment_progress__assignment__group__memberships__student=F("user_id"))
        )
    return records.select_related("user", "lesson")


def task_for(attempt):
    return IndependentAttemptAdmin._task(attempt)


def transcript_for(attempt) -> list[dict]:
    """Полный диалог (например, миссия «кафе»): реплики собеседника и все попытки ученика.

    В submitted хранятся только принятые реплики — для оценки уместности
    учителю нужен весь ход разговора. Только чтение; шаблон экранирует текст.
    """
    rows = (attempt.self_rubric or {}).get("transcript") or []
    out = []
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("text"), str):
            who = "Ученик" if row.get("who") == "You" else str(row.get("who") or "")[:40]
            out.append({"who": who, "text": row["text"][:400], "learner": row.get("who") == "You"})
    return out


class TeacherReviewForm(IndependentAttemptReviewForm):
    """Учитель меняет только заключение, три критерия и комментарий."""

    class Meta(IndependentAttemptReviewForm.Meta):
        fields = ["teacher_verdict", "teacher_note"]
        labels = {"teacher_verdict": "Заключение", "teacher_note": "Подсказка ученику"}
        help_texts = {"teacher_note": "Конкретно: что получилось и что поправить (от 20 символов). Ученик это увидит."}

    field_order = ["teacher_verdict", "rubric_meaning", "rubric_form", "rubric_context", "teacher_note"]


def save_review(form, teacher):
    attempt = form.save(commit=False)
    if attempt.teacher_verdict == IndependentAttempt.TeacherVerdict.UNREVIEWED:
        attempt.teacher_rubric, attempt.reviewed_by, attempt.reviewed_at = {}, None, None
    else:
        attempt.teacher_rubric = {axis: form.cleaned_data["rubric_" + axis] for axis in ("meaning", "form", "context")}
        attempt.reviewed_by, attempt.reviewed_at = teacher, timezone.now()
    attempt.save(update_fields=["teacher_verdict", "teacher_note", "teacher_rubric", "reviewed_by", "reviewed_at"])
    return attempt


class IssueForm(forms.Form):
    quote = forms.CharField(label="Где ошибка (можно скопировать фразу)", max_length=300, required=False)
    comment = forms.CharField(label="Что не так", max_length=2000, widget=forms.Textarea(attrs={"rows": 4}),
                              help_text="Например: «в переводе пропущено “не”» или «так американцы не говорят».")

    def clean_comment(self):
        text = self.cleaned_data["comment"].strip()
        if len(text) < 5:
            raise forms.ValidationError("Напишите хотя бы пару слов, что не так.")
        return text


class DraftForm(forms.ModelForm):
    class Meta:
        model = ContentDraft
        fields = ["kind", "level", "week", "title", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 18})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.curriculum.registry import LEVELS
        self.fields["level"] = forms.ChoiceField(label="Уровень", choices=[(lv.code, lv.code) for lv in LEVELS])
        self.fields["week"].min_value = 1

    def clean_week(self):
        week = self.cleaned_data.get("week")
        if week is not None and not 1 <= week <= 30:
            raise forms.ValidationError("Номер недели — от 1 до 30.")
        return week
