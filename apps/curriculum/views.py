from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.learning.models import WeekGoal
from apps.stories.script import build_lines

from .models import Level, TongueTwister, Week, WeekScene
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
        "weeks": level.week_set.select_related("scene"),
    })


@ensure_csrf_cookie
def week_detail(request, slug, number):
    level = next((lv for lv in Level.objects.all() if lv.slug == slug), None)
    if level is None:
        raise Http404
    week = get_object_or_404(Week, level=level, number=number)
    scene = WeekScene.objects.filter(week=week).prefetch_related("chunks__semantic_class__category").first()
    lines, speakers = build_lines(scene.script) if scene else ([], [])
    goal = WeekGoal.objects.filter(user=request.user, week=week).first() if request.user.is_authenticated else None
    return render(request, "curriculum/week.html", {
        "week": week, "scene": scene, "lines": lines, "speakers": speakers,
        "audio": scene.audio if scene else None,
        "lessons": week.lessons.filter(is_published=True),
        "twister": TongueTwister.objects.filter(week=week).first(), "goal": goal,
        "next_week": level.week_set.filter(number=number + 1).first(),
    })
