from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.core.a1_active import MAX_TOPIC, active_topics
from apps.learning.understanding import get_guide

from .models import Lesson


@ensure_csrf_cookie
def lesson_detail(request, slug):
    lesson = get_object_or_404(Lesson.objects.select_related("level", "focus"), slug=slug, is_published=True)
    extra_missions = None
    if lesson.level.code == "A1" and 1 <= lesson.order <= MAX_TOPIC:
        supplement = active_topics()[lesson.order]
        if supplement["slug"] == lesson.slug:
            extra_missions = supplement["missions"]
    units = lesson.units.select_related("semantic_class__category").order_by("uid")
    if getattr(settings, "EE_VOCABULARY_TRAINER_ENABLED", False) and request.user.is_authenticated:
        from apps.learning.trainer_service import register_legacy_exposure
        register_legacy_exposure(request.user, units)
    return render(request, "lessons/detail.html", {
        "lesson": lesson,
        "lesson_design_pilot": lesson.slug in {"a1-nouns-first-words", "a1-verb-be"},
        "extra_missions": extra_missions,
        "a1_pilot": lesson.level.code == "A1" and 1 <= lesson.order <= 28,
        "a1_guide": get_guide(lesson.slug) if lesson.level.code == "A1" else None,
        "layers": lesson.layers.all(),
        "units": units,
        "exercises": lesson.exercises.all(),
        "translations": lesson.practice_items.all(),
        "next_lesson": Lesson.objects.filter(is_published=True, level__order__gte=lesson.level.order)
        .exclude(pk=lesson.pk).filter(level=lesson.level, order__gt=lesson.order).first()
        or Lesson.objects.filter(is_published=True, level__order__gt=lesson.level.order).first(),
    })
