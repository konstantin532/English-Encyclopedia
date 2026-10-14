from django.contrib import admin

from apps.drills.models import Exercise

from .models import Lesson, LessonLayer


class LayerInline(admin.StackedInline):
    model = LessonLayer
    extra = 0


class ExerciseInline(admin.StackedInline):
    model = Exercise
    extra = 0


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ["title", "level", "week", "order", "is_published"]
    inlines = [LayerInline, ExerciseInline]
    filter_horizontal = ["units"]
