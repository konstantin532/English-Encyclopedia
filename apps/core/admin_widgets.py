"""Human-facing widgets; stored JSON and marker contracts stay unchanged."""
import json
from django import forms
from apps.taxonomy.registry import CATEGORIES, PALETTE, MARKERS
from apps.taxonomy.markup import find_issues
from apps.stories.script import voices_manifest


class AuthoringWidget(forms.Widget):
    template_name = "admin/widgets/authoring.html"

    class Media:
        css = {"all": ("css/admin-authoring.css",)}
        js = ("js/admin-authoring-model.js", "js/admin-authoring.js")

    def __init__(self, mode="marked", fields=None, attrs=None):
        super().__init__(attrs)
        self.mode = mode
        self.fields = fields or []

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.mode != "marked" and not isinstance(value, str):
            value = json.dumps(value if value is not None else [], ensure_ascii=False)
        context["widget"]["value"] = value or ("" if self.mode == "marked" else "[]")
        voices = voices_manifest()
        context["widget"]["config"] = json.dumps({
            "mode": self.mode, "fields": self.fields,
            "roles": {key: item["name_ru"] for key, item in voices.get("roles", {}).items()},
            "emotions": {key: item["name_ru"] for key, item in voices.get("emotions", {}).items()},
            "music": voices.get("music_moods", {}),
            "categories": [{"name": cat.name_ru, "classes": [{"id": f"{cat.code}{num}", "name": label, "color": PALETTE[num][1], "line": MARKERS[cat.marker][0], "style": MARKERS[cat.marker][1]} for num, label, _ in cat.classes]} for cat in CATEGORIES],
        }, ensure_ascii=False)
        return context


class StringListField(forms.Field):
    widget = forms.Textarea

    def prepare_value(self, value):
        return "\n".join(value) if isinstance(value, list) else value

    def to_python(self, value):
        if isinstance(value, list):
            return value
        return [line.strip() for line in (value or "").splitlines() if line.strip()]


class RecordListField(forms.JSONField):
    def __init__(self, *args, schema=(), **kwargs):
        self.schema = schema
        super().__init__(*args, **kwargs)

    def validate(self, value):
        super().validate(value)
        if value in self.empty_values:
            return
        if not isinstance(value, list):
            raise forms.ValidationError("Ожидается список карточек. Откройте редактор заново.")
        for i, row in enumerate(value, 1):
            if not isinstance(row, dict):
                raise forms.ValidationError(f"Карточка {i}: неверная структура.")
            for field in self.schema:
                if field["required"] and not str(row.get(field["key"], "")).strip():
                    raise forms.ValidationError(f"Карточка {i}: заполните «{field['label']}».")
                if field["key"] in row and not isinstance(row[field["key"]], str):
                    raise forms.ValidationError(f"Карточка {i}: «{field['label']}» должно быть текстом.")
                if field["kind"] == "marked" and find_issues(row.get(field["key"], "")):
                    raise forms.ValidationError(f"Карточка {i}: проверьте разметку в поле «{field['label']}».")


def record_field(schema, label, mode="records"):
    return RecordListField(required=False, label=label, schema=schema, widget=AuthoringWidget(mode, schema))


def spec(key, label, kind="text", required=False):
    return {"key": key, "label": label, "kind": kind, "required": required}
