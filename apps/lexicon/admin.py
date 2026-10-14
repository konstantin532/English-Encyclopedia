from django.contrib import admin

from .models import LexicalUnit


@admin.register(LexicalUnit)
class LexicalUnitAdmin(admin.ModelAdmin):
    list_display = ["uid", "lemma", "translation_ru", "part_of_speech", "semantic_class", "internal_level", "cefr", "verification_status"]
    list_filter = ["internal_level", "part_of_speech", "cefr", "verification_status"]
    search_fields = ["uid", "lemma", "translation_ru"]
