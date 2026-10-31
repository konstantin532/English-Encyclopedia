from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.core.a1_active import MAX_TOPIC, active_topics
from apps.learning.understanding import get_guide
from apps.teaching.assignments import start_assignment, student_assignment

from .models import Lesson


@ensure_csrf_cookie
def lesson_detail(request, slug):
    lesson = get_object_or_404(Lesson.objects.select_related("level", "focus"), slug=slug, is_published=True)
    progress = (
        start_assignment(request.user, student_assignment(request.user, request.GET["assignment"], lesson=lesson))
        if "assignment" in request.GET else None
    )
    extra_missions = None
    if lesson.level.code == "A1" and 1 <= lesson.order <= MAX_TOPIC:
        supplement = active_topics()[lesson.order]
        if supplement["slug"] == lesson.slug:
            extra_missions = supplement["missions"]
    units = lesson.units.select_related("semantic_class__category").order_by("uid")
    if getattr(settings, "EE_VOCABULARY_TRAINER_ENABLED", False) and request.user.is_authenticated:
        from apps.learning.trainer_service import register_legacy_exposure
        register_legacy_exposure(request.user, units)
    editorial_pilot = lesson.slug == "a1-cafe-order"
    glossary_units = list(units) if editorial_pilot else []
    return render(request, "lessons/detail.html", {
        "editorial_pilot": editorial_pilot,
        "editorial_words": [u for u in glossary_units if u.unit_type == "word"],
        "editorial_phrases": [u for u in glossary_units if u.unit_type != "word"],
        "lesson": lesson,
        "assignment_progress": progress,
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
