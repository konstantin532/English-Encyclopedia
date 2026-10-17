from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html
from apps.core.admin_widgets import AuthoringWidget, StringListField, record_field, spec
from apps.taxonomy.markup import find_issues
from apps.taxonomy.registry import CATEGORIES
from .models import Story
from .script import voices_manifest

SCRIPT_SCHEMA = [spec("speaker", "Кто говорит", required=True), spec("text", "Текст реплики", required=True), spec("kind", "Тип реплики"), spec("emotion", "Эмоция"), spec("music", "Музыка"), spec("spoken", "Произношение"), spec("ru", "Перевод")]


class StoryEditorForm(forms.ModelForm):
    script = record_field(SCRIPT_SCHEMA, "История по репликам", "script")
    questions = record_field([spec("q", "Вопрос", required=True), spec("a", "Ответ", required=True)], "Вопросы к истории")
    phrase_hunt = record_field([spec("phrase", "Выражение", required=True), spec("function", "Для чего используется", required=True)], "Полезные выражения")
    characters = StringListField(required=False, label="Персонажи", help_text="Каждое имя с новой строки, например Anna и Tom.")
    visual_cues = StringListField(required=False, label="Описания иллюстраций", help_text="Каждое описание с новой строки.")
    retell_words = StringListField(required=False, label="Слова для пересказа", help_text="По одному слову или выражению на строке.")
    retell_steps = StringListField(required=False, label="Шаги пересказа", help_text="Каждый шаг с новой строки.")
    focus = forms.MultipleChoiceField(required=False, label="Что тренируем", choices=[(c.code, c.name_ru) for c in CATEGORIES], widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Story
        fields = "__all__"
        widgets = {"body": AuthoringWidget()}
        labels = {"number": "Номер истории", "level": "Уровень", "week": "Неделя", "title": "Название", "hook_ru": "Завязка на русском", "grammar_ru": "Грамматика", "prediction_ru": "Вопрос перед чтением", "body": "Сплошной текст (если нет реплик)", "creative_ru": "Творческое задание", "new_units": "Новые слова из словаря", "is_published": "Опубликовать"}
        help_texts = {"body": "Если выше есть реплики, текст истории соберётся из них автоматически.", "script": "", "focus": "", "is_published": "Сначала сохраните черновик и проверьте текст, разметку и произношение."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["focus"] = list(self.instance.focus or "")

    def clean_focus(self):
        return "".join(self.cleaned_data["focus"])

    def clean_script(self):
        script = self.cleaned_data.get("script") or []
        voices = voices_manifest()
        for i, row in enumerate(script, 1):
            if row["speaker"] not in voices.get("roles", {}):
                raise forms.ValidationError(f"Реплика {i}: выберите персонажа из списка.")
            if row.get("kind", "speech") not in ("speech", "narration"):
                raise forms.ValidationError(f"Реплика {i}: выберите тип реплики.")
            for field, key in (("emotion", "emotions"), ("music", "music_moods")):
                if row.get(field) and row[field] not in voices.get(key, {}):
                    raise forms.ValidationError(f"Реплика {i}: неизвестное значение {field}.")
            for field in ("text", "spoken"):
                if find_issues(row.get(field, "")):
                    raise forms.ValidationError(f"Реплика {i}: проверьте учебную разметку текста.")
        # A changed sentence must not keep an unchanged, now-stale spoken variant.
        originals = self.instance.script if isinstance(self.instance.script, list) else []
        for row in script:
            if row.get("spoken"):
                previous = next((old for old in originals if old.get("speaker") == row.get("speaker") and old.get("spoken") == row["spoken"]), None)
                if previous is not None and previous.get("text") != row["text"]:
                    row.pop("spoken", None)
        return script

    def clean_body(self):
        body = self.cleaned_data.get("body", "")
        if find_issues(body):
            raise forms.ValidationError("Проверьте учебную разметку текста.")
        return body

    def clean(self):
        data = super().clean()
        if data.get("is_published") and not (data.get("script") or data.get("body", "").strip()):
            raise forms.ValidationError("Перед публикацией добавьте текст истории или хотя бы одну реплику.")
        return data


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    form = StoryEditorForm
    list_display = ("number", "title", "level", "week", "is_published")
    list_filter = ("level", "is_published")
    search_fields = ("title", "hook_ru")
    filter_horizontal = ("new_units",)
    readonly_fields = ("editor_guide", "audio_status", "scene_background")
    fieldsets = (
        ("Как работать с историей", {"fields": ("editor_guide",)}),
        ("Об истории", {"fields": ("number", "title", "level", "week", "hook_ru", "grammar_ru", "focus")}),
        ("Текст и реплики", {"fields": ("script", "characters")}),
        ("Сплошной текст вместо реплик", {"fields": ("body",), "classes": ("collapse",), "description": "Используется, только если список реплик пуст. При наличии реплик текст собирается из них."}),
        ("Задания для ученика", {"fields": ("prediction_ru", "visual_cues", "questions", "phrase_hunt", "retell_words", "retell_steps", "creative_ru", "new_units")}),
        ("Публикация и озвучка", {"fields": ("is_published", "audio_status", "scene_background")}),
    )

    @admin.display(description="Памятка редактора")
    def editor_guide(self, obj):
        return format_html('<div class="ee-guide"><strong>Пишите историю, а не код.</strong><ol><li>Заполните название, уровень и неделю.</li><li>Добавьте реплики: выберите персонажа и напишите текст обычными словами.</li><li>Для разметки выделите слово и выберите его часть речи и значение. Программа добавит служебные обозначения сама.</li><li>Сохраните черновик, проверьте текст и только затем включите публикацию.</li></ol><p>Если меняете текст реплики, проверьте разговорную форму: неизменённый старый вариант будет снят при сохранении. Произношение заполняйте, только если оно отличается от текста: например, It is → It’s. Новые слова автоматически по частям речи не определяются.</p><p>Изменение текста не создаёт новую озвучку. Новая озвучка по текущему тексту подготавливается и подключается отдельно; обычный генератор исходных материалов её не заменяет.</p></div>')

    @admin.display(description="Озвучка")
    def audio_status(self, obj):
        return "Есть сохранённая озвучка. После изменения реплик требуется генерация заново." if obj and obj.audio else "Озвучки пока нет. Она создаётся генератором, вручную это поле не редактируется."

    @admin.display(description="Фон сцены")
    def scene_background(self, obj):
        return "Фон настроен. Он подготавливается вместе с озвучкой." if obj and obj.ambience else "Фон сцены не задан."

    def save_model(self, request, obj, form, change):
        if obj.script:
            obj.body = "\n\n".join(row["text"] for row in obj.script)
        if change and any(key in form.changed_data for key in ("script", "body")):
            obj.audio = {}
            self.message_user(request, "Текст изменён. Прежняя озвучка отключена, чтобы ученик не слышал другой текст. Новую озвучку нужно подготовить по текущему тексту и подключить отдельно.", messages.WARNING)
        super().save_model(request, obj, form, change)
