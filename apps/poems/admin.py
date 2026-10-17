from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html
import re
from apps.core.admin_widgets import AuthoringWidget, StringListField
from apps.taxonomy.markup import find_issues, strip_markup
from .models import Poem


class PoemEditorForm(forms.ModelForm):
    workshop = forms.JSONField(label="Текст, произношение и задания", required=False, widget=AuthoringWidget("poem"))
    phonetic_goals = StringListField(label="Цели произношения", required=False, help_text="По одной цели с новой строки: например звук /ð/ или ритм фразы.")

    class Meta:
        model = Poem
        exclude = ("body", "pronunciation", "gaps")
        labels = {"number": "Номер произведения", "level": "Уровень", "week": "Неделя", "title": "Название", "rhyme_scheme": "Схема рифмы", "theme_ru": "Тема и цель", "target_units": "Слова для закрепления", "is_published": "Опубликовать"}
        help_texts = {"rhyme_scheme": "Необязательно. Например AABB. Для скороговорки можно оставить пустым.", "is_published": "Оставьте выключенным, пока текст и задания не проверены."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["workshop"] = {"body": self.instance.body or "", "pronunciation": self.instance.pronunciation or [], "gaps": self.instance.gaps or []}
            if not self.instance.pk:
                self.initial["is_published"] = False

    def clean_workshop(self):
        data = self.cleaned_data.get("workshop") or {"body": "", "pronunciation": [], "gaps": []}
        if not isinstance(data, dict) or not isinstance(data.get("body"), str):
            raise ValidationError("Не удалось прочитать текст. Откройте редактор заново.")
        body = data["body"]
        if find_issues(body):
            raise ValidationError("Проверьте учебную разметку текста.")
        lines = [strip_markup(line) for line in body.splitlines() if line.strip()]
        pronunciation, gaps = data.get("pronunciation", []), data.get("gaps", [])
        if not isinstance(pronunciation, list) or len(pronunciation) > len(lines):
            raise ValidationError("Число подсказок произношения не должно превышать число строк текста.")
        for i, note in enumerate(pronunciation, 1):
            if not isinstance(note, dict) or any(key in note and not isinstance(note[key], str) for key in ("stress", "ipa", "ru")):
                raise ValidationError(f"Строка {i}: подсказки произношения должны быть текстом.")
        if not isinstance(gaps, list):
            raise ValidationError("Не удалось прочитать упражнение с пропусками.")
        used = set()
        for gap in gaps:
            if not isinstance(gap, dict) or type(gap.get("line")) is not int or not isinstance(gap.get("word"), str):
                raise ValidationError("Выберите слово для пропуска в строке текста.")
            index, word = gap["line"], gap["word"].strip()
            if not 1 <= index <= len(lines) or not word or index in used:
                raise ValidationError("У каждой строки может быть один пропуск; пустые строки не нумеруются.")
            if not re.search(rf"\b{re.escape(word)}\b", lines[index-1], re.I):
                raise ValidationError(f"Строка {index}: слова «{word}» нет в тексте.")
            used.add(index)
        return {"body": body, "pronunciation": pronunciation, "gaps": gaps}

    def clean(self):
        data = super().clean()
        if data.get("is_published") and not data.get("workshop", {}).get("body", "").strip():
            raise ValidationError("Перед публикацией добавьте текст произведения.")
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        data = self.cleaned_data["workshop"]
        obj.body, obj.pronunciation, obj.gaps = data["body"], data["pronunciation"], data["gaps"]
        if commit:
            obj.save()
            self.save_m2m()
        return obj


@admin.register(Poem)
class PoemAdmin(admin.ModelAdmin):
    form = PoemEditorForm
    list_display = ("number", "title", "level", "week", "is_published")
    list_filter = ("level", "is_published")
    search_fields = ("title", "theme_ru")
    filter_horizontal = ("target_units",)
    readonly_fields = ("editor_guide",)
    fieldsets = (
        ("Как работать со стихом и скороговоркой", {"fields": ("editor_guide",)}),
        ("О произведении", {"fields": ("number", "title", "level", "week", "theme_ru", "rhyme_scheme", "phonetic_goals")}),
        ("Текст и тренировка", {"fields": ("workshop",)}),
        ("Публикация", {"fields": ("target_units", "is_published")}),
    )

    @admin.display(description="Памятка редактора")
    def editor_guide(self, obj):
        return format_html('<div class="ee-guide"><strong>Пишите обычными строками.</strong><ol><li>Введите или вставьте стих целиком. Пустая строка разделяет строфы.</li><li>Разметку слов настройте через «Разметка слов»: выберите слово, часть речи и значение.</li><li>В разделе «Произношение и пропуски по строкам» откройте нужную строку. При необходимости добавьте транскрипцию, подсказку ударений или русскую подсказку.</li><li>Слово для пропуска выбирается из слов этой строки. Номера строк редактор поддерживает сам.</li><li>Сохраните черновик, проверьте его на сайте и затем опубликуйте.</li></ol><p>При изменении текста подсказки и пропуски сохраняются у неизменённых строк. Для изменённых строк они снимаются, чтобы не показывать устаревшее произношение. Пустые строки между строфами не считаются строками упражнения.</p></div>')
