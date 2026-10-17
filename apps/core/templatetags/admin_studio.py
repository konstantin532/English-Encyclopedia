"""Permission-aware presentation data for the editorial admin dashboard."""
from django import template
from django.contrib import admin

register = template.Library()

APP_LABELS = {"accounts": "Команда и доступ", "auth": "Права доступа", "curriculum": "Программа курса", "lessons": "Уроки и практика", "lexicon": "Словарь", "stories": "Истории", "poems": "Стихи и произношение", "taxonomy": "Атлас языка"}
MODEL_LABELS = {"week": "Недели", "story": "Истории", "poem": "Стихи и скороговорки"}
DESCRIPTIONS = {"curriculum": "Путь от первого слова к свободной речи", "lessons": "Объяснения, ситуации и самостоятельная практика", "lexicon": "Слова, выражения и живые примеры", "stories": "Сюжеты, диалоги и озвучка", "poems": "Ритм, интонация и работа со звуком", "taxonomy": "Части речи и система визуальных маркеров", "accounts": "Пользователи и доступ к платформе", "auth": "Группы и разрешения"}
ORDER = {name: i for i, name in enumerate(("curriculum", "lessons", "lexicon", "stories", "poems", "taxonomy", "accounts", "auth"))}

@register.filter
def studio_apps(apps):
    result = []
    for app in apps:
        item = {**app, "name": APP_LABELS.get(app["app_label"], app["name"]), "description": DESCRIPTIONS.get(app["app_label"], "Материалы и настройки")}
        item["models"] = [{**m, "name": MODEL_LABELS.get(m["object_name"].lower(), m["name"])} for m in app["models"]]
        result.append(item)
    return sorted(result, key=lambda item: ORDER.get(item["app_label"], 99))

@register.simple_tag(takes_context=True)
def studio_metrics(context):
    request = context["request"]
    cards = []
    for label, name, title in (("curriculum", "week", "Недель курса"), ("lessons", "lesson", "Уроков"), ("lexicon", "lexicalunit", "Единиц в словаре"), ("stories", "story", "Историй")):
        for model, model_admin in admin.site._registry.items():
            if model._meta.label_lower != f"{label}.{name}":
                continue
            if not model_admin.has_view_or_change_permission(request):
                continue
            queryset = model_admin.get_queryset(request)
            card = {"title": title, "count": queryset.count(), "url": None, "published": None}
            from django.urls import reverse
            card["url"] = reverse(f"admin:{label}_{name}_changelist")
            if any(field.name == "is_published" for field in model._meta.fields):
                card["published"] = queryset.filter(is_published=True).count()
            cards.append(card)
    return cards
