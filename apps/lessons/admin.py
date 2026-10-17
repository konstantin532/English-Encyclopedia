from django import forms
from django.contrib import admin
from django.utils.html import format_html
from apps.core.admin_widgets import AuthoringWidget, StringListField, record_field, spec
from apps.drills.models import Exercise
from apps.taxonomy.markup import find_issues
from .models import Lesson, LessonLayer


class LessonEditorForm(forms.ModelForm):
    sound_notes = record_field([spec("text", "Слово или фраза", "marked", True), spec("ipa", "Международная транскрипция"), spec("ru", "Русская подсказка"), spec("note_ru", "Пояснение")], "Заметки о произношении")
    contractions = record_field([spec("full", "Полная форма", "marked", True), spec("short", "Сокращённая форма", "marked", True), spec("ipa", "Транскрипция"), spec("ru", "Русская подсказка"), spec("note_ru", "Пояснение")], "Сокращения")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.instance.pk:
            self.initial["is_published"] = False

    class Meta:
        model = Lesson
        fields = "__all__"
        labels = {"slug": "Адрес урока", "level": "Уровень", "week": "Неделя", "order": "Порядок в курсе", "title": "Название", "summary": "Краткое описание", "focus": "Основная часть речи", "units": "Слова урока", "minutes": "Время на урок, минут", "is_published": "Опубликовать"}
        help_texts = {"slug": "Короткий уникальный адрес латинскими буквами, например my-new-home.", "is_published": "Снимите отметку, пока урок не готов для учеников."}


class LayerEditorForm(forms.ModelForm):
    class Meta:
        model = LessonLayer
        fields = "__all__"
        widgets = {"body": AuthoringWidget()}
        labels = {"number": "Раздел объяснения", "body": "Объяснение и примеры"}
        help_texts = {"body": "Пишите обычный текст. Пустая строка начинает новый абзац. Для английского примера начните строку с > и пробела; для пункта списка — с - и пробела. Разметка слов назначается кнопками редактора."}


class ExerciseEditorForm(forms.ModelForm):
    options = StringListField(required=False, label="Варианты ответа", help_text="Каждый вариант с новой строки. Кавычки и скобки не нужны.")
    accepted = StringListField(required=False, label="Другие правильные ответы", help_text="Каждый допустимый ответ с новой строки.")

    class Meta:
        model = Exercise
        fields = "__all__"
        widgets = {"prompt_en": AuthoringWidget()}
        labels = {"order": "Номер задания", "kind": "Тип задания", "stage": "Этап практики", "prompt_ru": "Инструкция по-русски", "prompt_en": "Текст задания по-английски", "answer": "Правильный ответ", "hint_ru": "Подсказка", "explanation_ru": "Объяснение ответа", "units": "Слова задания"}
        help_texts = {"answer": "Для сборки фразы напишите целую фразу в правильном порядке.", "prompt_en": "Пропущенное слово обозначайте тремя подчёркиваниями: ___."}

    def clean_prompt_en(self):
        value = self.cleaned_data.get("prompt_en", "")
        if find_issues(value):
            raise forms.ValidationError("Проверьте разметку текста задания.")
        return value


class LayerInline(admin.StackedInline):
    model = LessonLayer
    form = LayerEditorForm
    extra = 0
    verbose_name = "раздел объяснения"
    verbose_name_plural = "Семь разделов объяснения"


class ExerciseInline(admin.StackedInline):
    model = Exercise
    form = ExerciseEditorForm
    extra = 0
    verbose_name = "задание"
    verbose_name_plural = "Практические задания"
    filter_horizontal = ("units",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    form = LessonEditorForm
    list_display = ["title", "level", "week", "order", "is_published"]
    list_filter = ("level", "is_published")
    search_fields = ("title", "summary")
    inlines = [LayerInline, ExerciseInline]
    filter_horizontal = ["units"]
    readonly_fields = ("editor_guide",)
    fieldsets = (
        ("Как создать урок", {"fields": ("editor_guide",)}),
        ("Основное", {"fields": ("title", "summary", "level", "week", "order", "minutes", "focus", "slug", "units", "is_published")}),
        ("Звучание и сокращения", {"fields": ("sound_notes", "contractions"), "classes": ("collapse",)}),
    )

    @admin.display(description="Памятка редактора")
    def editor_guide(self, obj):
        return format_html('<div class="ee-guide"><strong>Урок собирается из объяснений и заданий.</strong><ol><li>Заполните название, описание, уровень и неделю. Для черновика снимите «Опубликовать».</li><li>Ниже нажмите «Добавить ещё один раздел объяснения», выберите раздел и напишите текст.</li><li>Выделите английское слово и выберите его часть речи и значение — служебные коды вводить не нужно.</li><li>Добавьте задание: тип, инструкцию, варианты и правильный ответ. Каждый вариант пишется с новой строки.</li><li>Сохраните урок, проверьте его на сайте и затем опубликуйте.</li></ol><p>Новые слова автоматически по частям речи не определяются: значение зависит от контекста. Существующая разметка сохраняется у неизменённых слов.</p></div>')
