from django.conf import settings
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


# Живописные обложки «Атласа живого языка»: герои одни и те же во всём курсе.
# Для остальных недель A1 остаются векторные главы, для новых уровней — нейтральная обложка.
A1_PAINTED = {
    1: ("a1-w01", "Анна с кружкой у крыльца знакомится с соседом Томом"),
    2: ("a1-w02", "Анна, Том и Мия разглядывают загадочную коробку на новой кухне"),
    3: ("a1-w03", "Анна в кафе с семейной фотографией, Мия у кофемашины, Том у стойки"),
    4: ("a1-w04", "Анна показывает Тому и Мии семейное фото за столиком кафе"),
    5: ("a1-w05", "Анна и Том покупают яблоки и молоко в магазинчике у дома"),
    6: ("a1-w06", "Семь утра в кафе Мии: Анна, Том и рыжий кот у двери"),
    7: ("a1-w07", "Вечерний разговор о работе в кафе"),
    8: ("a1-w08", "Пожилая женщина объясняет Анне и Тому дорогу к мастерской"),
    9: ("a1-w09", "Мастер в мастерской рассматривает старинный ключ"),
    10: ("a1-w10", "Субботнее утро в кафе: Анна с книгой, Том с гитарой, Мия и кот Box"),
    11: ("a1-w11", "Том на приёме у врача"),
    12: ("a1-w12", "Анна и Том отправляют письмо на почте"),
    13: ("a1-w13", "Анна учит Тома и Мию русским буквам в кафе"),
    14: ("a1-w14", "Анна и Том в автобусе со старым фото, водитель автобуса"),
}
LEVEL_TITLES = {
    "A1": "Первые шаги", "A1+": "Первые истории", "A2": "Уверенный старт", "A2+": "Свободнее каждый день",
    "B1": "Самостоятельность", "B1+": "Глубже в язык", "B2": "Свобода речи", "B2+": "Язык кино",
}


def week_art(level_code, week_number):
    """Обложка недели: живописная, иначе векторная глава A1, иначе None."""
    painted = A1_PAINTED.get(week_number) if level_code == "A1" else None
    if painted:
        key, alt = painted
        return {"src": static(f"img/atlas/{key}-800.webp"), "large": static(f"img/atlas/{key}-1536.webp"),
                "alt": alt, "painted": True}
    svg = a1_atlas_cover(level_code, week_number)
    if svg:
        return {"src": svg, "large": svg, "alt": A1_ATLAS_ALT[week_number - 1], "painted": False}
    return None


def level_detail(request, slug):
    all_levels = list(Level.objects.all())
    level = next((lv for lv in all_levels if lv.slug == slug), None)
    if level is None:
        raise Http404
    weeks = list(level.week_set.select_related("scene"))
    for week in weeks:
        week.atlas_cover_url = a1_atlas_cover(level.code, week.number)
        week.art = week_art(level.code, week.number)
    return render(request, "curriculum/level.html", {
        "level": level,
        "level_title": LEVEL_TITLES.get(level.code, ""),
        "level_art": static("img/atlas/level-a1-1400.webp"),
        "weeks_ready": sum(1 for w in weeks if getattr(w, "scene", None)),
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
    trainer_entry = (getattr(settings, "EE_VOCABULARY_TRAINER_ENABLED", False)
                     and request.user.is_authenticated and level.code == "A1" and week.number == 3)
    if trainer_entry and scene:
        from apps.learning.trainer_service import register_legacy_exposure
        # These three authored targets are visible in week 3 dialogue/chunks;
        # tea is in the dialogue but is not a scene.chunks relation.
        register_legacy_exposure(request.user, ["LX-00055", "LX-00285", "LX-00084"])
    return render(request, "curriculum/week.html", {
        "trainer_entry": trainer_entry,
        "week": week, "scene": scene, "lines": lines, "speakers": speakers,
        "atlas_cover_url": (week_art(level.code, week.number) or {}).get("large"),
        "atlas_cover_alt": (week_art(level.code, week.number) or {}).get("alt", ""),
        "audio": scene.audio if scene else None,
        "lessons": week.lessons.filter(is_published=True),
        "twister": TongueTwister.objects.filter(week=week).first(), "goal": goal,
        "next_week": level.week_set.filter(number=number + 1).first(),
    })
