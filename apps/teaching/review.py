"""Проверка свободных ответов учителем. Те же правила, что в админке (apps/learning/admin.py)."""
from django import forms
from django.utils import timezone

from apps.learning.admin import IndependentAttemptAdmin, IndependentAttemptReviewForm
from apps.learning.models import IndependentAttempt

from .access import visible_students

NEEDS_HUMAN = (IndependentAttempt.Outcome.NEEDS_REVIEW, IndependentAttempt.Outcome.SELF_REPORTED)


def review_queue(teacher):
    """Непроверенные свободные ответы видимых учителю учеников, старые сверху."""
    return (IndependentAttempt.objects
            .filter(user__in=visible_students(teacher), outcome__in=NEEDS_HUMAN,
                    teacher_verdict=IndependentAttempt.TeacherVerdict.UNREVIEWED)
            .select_related("user", "lesson").order_by("created_at"))


def reviewable(teacher):
    return IndependentAttempt.objects.filter(user__in=visible_students(teacher)).select_related("user", "lesson")


def task_for(attempt):
    return IndependentAttemptAdmin._task(attempt)


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
