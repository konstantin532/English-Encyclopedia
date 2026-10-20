"""Аудирование, диктант и перевод: поиск звука реплики и выдача заданий уроку.

Звук берётся из уже озвученного диалога недели (manifest.json -> WeekScene.audio):
отрезок одной реплики по таймингам. Если озвучки нет, задание со звуком скрывается,
а не ломает страницу.
"""
from django.templatetags.static import static
from django.urls import reverse

from apps.curriculum.models import WeekScene

from .models import PracticeItem

TEMPOS = ("very_slow", "slow", "natural")


def week_script(level, week_number: int) -> list:
    scene = WeekScene.objects.filter(week__level=level, week__number=week_number).first()
    return scene.script if scene else []


def clip_for(item: PracticeItem, scenes: dict | None = None) -> dict | None:
    """{"src", "start", "end"} для реплики задания или None, если звука нет."""
    ref = item.audio_line or {}
    week, line, tempo = ref.get("week"), ref.get("line"), ref.get("tempo", "slow")
    if type(week) is not int or type(line) is not int or tempo not in TEMPOS:
        return None
    key = (item.lesson.level_id, week)
    if scenes is None or key not in scenes:
        scene = WeekScene.objects.filter(week__level_id=item.lesson.level_id, week__number=week).first()
        if scenes is not None:
            scenes[key] = scene
    else:
        scene = scenes[key]
    entry = (scene.audio or {}).get(tempo) if scene else None
    if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
        return None
    timings = entry.get("timings")
    if not isinstance(timings, list) or not 0 <= line < len(timings):
        return None
    segment = timings[line]
    if not isinstance(segment, dict) or segment.get("line") != line:
        return None
    start, end = segment.get("start"), segment.get("end")
    if type(start) not in (int, float) or type(end) not in (int, float) or end <= start:
        return None
    return {"src": static(entry["file"]), "start": round(float(start), 3), "end": round(float(end), 3)}


def available_items(lesson, scenes: dict | None = None) -> list[PracticeItem]:
    """Задания урока, которые можно показать: задания со звуком без озвучки скрыты."""
    scenes = {} if scenes is None else scenes
    out = []
    for item in lesson.practice_items.select_related("lesson").all():
        item.clip = clip_for(item, scenes) if item.needs_audio else None
        if item.needs_audio and item.clip is None:
            continue
        item.check_url = reverse("api:check_practice", args=[item.pk])
        out.append(item)
    return out


def review_exercise(item: PracticeItem):
    """Основное задание урока, чьё отложенное повторение назначается после ошибки."""
    return item.lesson.exercises.filter(order=item.review_of).first()
