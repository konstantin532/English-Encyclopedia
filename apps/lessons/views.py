from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Lesson


@ensure_csrf_cookie
def lesson_detail(request, slug):
    lesson = get_object_or_404(Lesson.objects.select_related("level", "focus"), slug=slug, is_published=True)
    units = lesson.units.select_related("semantic_class__category").order_by("uid")
    return render(request, "lessons/detail.html", {
        "lesson": lesson,
        "layers": lesson.layers.all(),
        "units": units,
        "exercises": lesson.exercises.all(),
        "next_lesson": Lesson.objects.filter(is_published=True, level__order__gte=lesson.level.order)
        .exclude(pk=lesson.pk).filter(level=lesson.level, order__gt=lesson.order).first()
        or Lesson.objects.filter(is_published=True, level__order__gt=lesson.level.order).first(),
    })
