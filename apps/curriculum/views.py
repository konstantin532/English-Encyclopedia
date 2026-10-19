from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.learning.models import WeekGoal
from apps.stories.script import build_lines

from .models import Level, TongueTwister, Week, WeekScene
from .registry import LEVEL_BY_CODE


# Describes the artwork, not unverified character biography or unseen story events.
A1_ATLAS_ALT = (
    "Анна и Том у входа в новый дом",
    "Домашний интерьер и кот Box",
    "Мия за стойкой небольшого кафе",
    "Семейная фотография в рамке",
    "Витрина небольшого магазина у дома",
    "Кафе Мии утром: стойка и настенные часы",
    "Вечернее кафе Мии — место разговора о работе",
    "Городская улица и указатель направлений",
    "Телефон как образ разговора с мастерской",
    "Субботнее утро в кафе Мии",
    "Спокойный интерьер врачебного кабинета",
    "Почтовая стойка и письмо",
    "Вечер в кафе Мии: открытая тетрадь как образ будущего урока",
    "Автобус на фоне городских улиц",
)


def a1_atlas_cover(level_code, week_number):
    """The A1 illustration series is complete for weeks 1–14 only."""
    if level_code != "A1" or not 1 <= week_number <= 14:
        return None
    return static(f"img/studio/a1-week-{week_number:02d}.svg")


def level_detail(request, slug):
    all_levels = list(Level.objects.all())
    level = next((lv for lv in all_levels if lv.slug == slug), None)
    if level is None:
        raise Http404
    weeks = list(level.week_set.select_related("scene"))
    for week in weeks:
        week.atlas_cover_url = a1_atlas_cover(level.code, week.number)
    return render(request, "curriculum/level.html", {
        "level": level,
        "all_levels": all_levels,
        "plan": LEVEL_BY_CODE[level.code],
        "lessons": level.lessons.filter(is_published=True),
        "units_ready": level.units.count(),
        "weeks": weeks,
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
        "atlas_cover_url": a1_atlas_cover(level.code, week.number),
        "atlas_cover_alt": A1_ATLAS_ALT[week.number - 1] if level.code == "A1" and 1 <= week.number <= 14 else "",
        "audio": scene.audio if scene else None,
        "lessons": week.lessons.filter(is_published=True),
        "twister": TongueTwister.objects.filter(week=week).first(), "goal": goal,
        "next_week": level.week_set.filter(number=number + 1).first(),
    })
