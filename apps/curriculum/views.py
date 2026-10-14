from django.http import Http404
from django.shortcuts import render

from .models import Level
from .registry import LEVEL_BY_CODE


def level_detail(request, slug):
    all_levels = list(Level.objects.all())
    level = next((lv for lv in all_levels if lv.slug == slug), None)
    if level is None:
        raise Http404
    return render(request, "curriculum/level.html", {
        "level": level,
        "all_levels": all_levels,
        "plan": LEVEL_BY_CODE[level.code],
        "lessons": level.lessons.filter(is_published=True),
        "units_ready": level.units.count(),
    })
