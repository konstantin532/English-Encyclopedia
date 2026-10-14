from django.contrib import admin

from .models import PartOfSpeech, SemanticClass


class ReadOnlyRegistry(admin.ModelAdmin):
    """Реестр задаётся в коде (registry.py); в админке только просмотр."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PartOfSpeech)
class PartOfSpeechAdmin(ReadOnlyRegistry):
    list_display = ["order", "key", "code", "name_ru", "marker"]


@admin.register(SemanticClass)
class SemanticClassAdmin(ReadOnlyRegistry):
    list_display = ["class_id", "name_ru", "name_en", "color"]
    list_filter = ["category"]
