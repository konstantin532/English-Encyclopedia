"""Проверки недель вокруг ситуаций: сцены, реплики, скороговорки, сферы, музыка историй.

Спецификация: docs/specs/2026-10-14-situation-weeks.md, разделы 8a и 9.
"""
import re

from apps.curriculum.models import Level, TongueTwister, Week, WeekScene
from apps.curriculum.registry import DIALOGUE_LINES, DIALOGUE_WORDS, SPHERES, TWISTER_SERIES
from apps.lexicon.models import UnitType
from apps.lessons.models import Lesson
from apps.stories.models import Story
from apps.stories.script import voices_manifest
from apps.taxonomy.markup import strip_markup
from apps.taxonomy.registry import CATEGORIES

MARKER_TOKEN = re.compile(r"\[([A-Z])(\d+)(?:-#[0-9a-fA-F]{6})?\]")
QUOTES = re.compile(r"[“”\"«»]")
SENTENCE = re.compile(r"[^.!?]+[.!?]")


def normalize_line(text: str) -> str:
    """Строка без разметки, кавычек и лишних пробелов, в нижнем регистре — для сравнения реплик и примеров."""
    return " ".join(QUOTES.sub("", strip_markup(text)).split()).casefold()


def marker_count(script: list[dict], code: str) -> int:
    """Сколько раз маркер встречается в репликах: «D» — любой класс категории, «D1» — только класс."""
    n = 0
    for line in script:
        for cat, num in MARKER_TOKEN.findall(line.get("text", "")):
            if cat == code[0] and (len(code) == 1 or num == code[1:]):
                n += 1
    return n


def marker_in_registry(code: str) -> bool:
    for cat in CATEGORIES:
        if cat.code == code[:1]:
            return len(code) == 1 or (code[1:].isdigit() and int(code[1:]) in {c[0] for c in cat.classes})
    return False


def lesson_examples(lesson) -> set[str]:
    """Английские части примеров «> » во всех слоях урока."""
    out = set()
    for layer in lesson.layers.all():
        for raw in layer.body.splitlines():
            if raw.startswith("> "):
                out.add(normalize_line(raw[2:].split(" — ")[0]))
    return out


BLENDS = {"gonna", "wanna", "gotta", "gimme", "lemme", "kinda", "sorta", "whatcha", "dunno", "y'all"}
SHORTENABLE = re.compile(r"\b(?:I am|it is|is not|are not|do not|does not|you are|that is|he is|she is|here is|what is|who is|can not|cannot)\b", re.I)
# Утвердительный be в конце короткого ответа не сокращают: Yes, I am. Here you are.
FINAL_BE = {"i am", "it is", "you are", "that is", "he is", "she is", "here is", "what is", "who is"}

# Напоминание добавить вариант «как говорят» (spoken): все недели этих уровней и все истории.
SPOKEN_REMINDER_LEVELS = {"A1", "A1+", "A2"}


def audit_script(r, where: str, script: list[dict], voices: dict, music_required: bool = False,
                 level=None, week_number: int = 99, warn_spoken: bool = False) -> None:
    """Общие правила реплик: роль, эмоция, настроение музыки."""
    from apps.publishing.audit import audit_contractions, text_tokens, vocab_until

    vocab = vocab_until(level, week_number) if level else set()
    roles, emotions, moods = voices.get("roles", {}), voices.get("emotions", {}), voices.get("music_moods", {})
    if music_required and script and "music" not in script[0]:
        r.errors.append(f"{where}: у первой реплики нет music.")
    for i, line in enumerate(script, 1):
        text, spoken = line.get("text", ""), line.get("spoken", "")
        at = f"{where}, реплика {i}"
        audit_contractions(r, at, text)
        if spoken:
            audit_contractions(r, at, spoken)
            from apps.taxonomy.markup import find_issues

            for issue in find_issues(spoken):
                r.errors.append(f"{at}: spoken: {issue.token} — {issue.problem}.")
            if normalize_line(spoken) == normalize_line(text):
                r.errors.append(f"{at}: spoken совпадает с text.")
            if level:
                stray = _unknown(spoken, vocab)
                if stray:
                    r.errors.append(f"{at}: незнакомые слова в spoken: {', '.join(stray)}.")
                if level.code in {"A1", "A1+", "A2"}:
                    for blend in sorted({t.lower().replace("’", "'") for t in text_tokens(spoken)} & BLENDS):
                        r.errors.append(f"{at}: слияние {blend} рано для уровня {level.code}.")
        elif warn_spoken:
            plain = strip_markup(text)
            forms = []
            for match in SHORTENABLE.finditer(plain):
                form = match.group().lower()
                # Утвердительный be в конце короткого ответа не сокращается: Yes, I am.
                if form in FINAL_BE and not re.match(r"\s+[A-Za-z]", plain[match.end():]):
                    continue
                if form not in forms:
                    forms.append(form)
            if forms:
                r.warnings.append(f"{at}: можно сократить {', '.join(forms)} — добавьте spoken.")
        if line.get("speaker") not in roles:
            r.errors.append(f"{where}, реплика {i}: роли {line.get('speaker')} нет в voices.yaml.")
        emotion = line.get("emotion", "neutral")
        if emotion not in emotions:
            r.errors.append(f"{where}, реплика {i}: неизвестная эмоция {emotion}.")
        if "music" in line and line["music"] not in moods:
            r.errors.append(f"{where}, реплика {i}: неизвестное настроение {line['music']}.")


def _unknown(text: str, vocab: set[str]) -> list[str]:
    from apps.publishing.audit import is_known, text_tokens

    return sorted({t.lower() for t in text_tokens(text) if not is_known(t, vocab)})


def audit_scene(r, scene: WeekScene, voices: dict) -> None:
    from apps.publishing.audit import text_tokens, vocab_until

    week = scene.week
    level = week.level
    where = f"Неделя {level.code}-{week.number}"
    script = scene.script or []
    if not scene.can_do_ru.strip():
        r.errors.append(f"{where}: нет цели «Я смогу…».")
    if not script:
        r.errors.append(f"{where}: нет диалога.")
    if not scene.mission_ru.strip():
        r.errors.append(f"{where}: нет задания в жизнь.")
    lessons = list(week.lessons.prefetch_related("layers"))
    if not lessons:
        r.errors.append(f"{where}: нет ни одного урока.")
    audit_script(r, where, script, voices, level=level, week_number=week.number,
                 warn_spoken=level.code in SPOKEN_REMINDER_LEVELS)

    text = " ".join(line.get("text", "") for line in script)
    vocab = vocab_until(level, week.number)
    stray = _unknown(text, vocab)
    if stray:
        r.errors.append(f"{where}: незнакомые слова в диалоге: {', '.join(stray)}.")

    for code in week.grammar_markers or []:
        if not marker_in_registry(code):
            r.errors.append(f"{where}: маркера {code} нет в реестре.")
            continue
        n = marker_count(script, code)
        if n < 2:
            r.errors.append(f"{where}: маркер {code} встречается {n} раз, нужно не меньше 2.")

    lines = set()
    for line in script:
        plain = normalize_line(line.get("text", ""))
        lines.add(plain)
        lines |= {s.strip() for s in SENTENCE.findall(plain)}
    for lesson in lessons:
        if not lesson_examples(lesson) & lines:
            r.errors.append(f"{where}: в уроке {lesson.slug} нет примера из диалога недели.")

    if level.code in DIALOGUE_LINES:
        lo, hi = DIALOGUE_LINES[level.code]
        if not lo <= len(script) <= hi:
            r.errors.append(f"{where}: реплик {len(script)}, норма {lo}–{hi}.")
        lo, hi = DIALOGUE_WORDS[level.code]
        words = len(text_tokens(text))
        if not lo <= words <= hi:
            r.errors.append(f"{where}: слов в диалоге {words}, норма {lo}–{hi}.")
    else:
        r.warnings.append(f"{where}: нет нормы длины диалога для уровня {level.code}.")

    chunks = list(scene.chunks.all())
    if not 5 <= len(chunks) <= 8:
        r.warnings.append(f"{where}: готовых фраз {len(chunks)}, нужно 5–8.")
    for u in chunks:
        if u.unit_type != UnitType.PHRASE:
            r.warnings.append(f"{where}: готовая фраза {u.uid} не типа phrase.")
    if not TongueTwister.objects.filter(week=week).exists():
        r.warnings.append(f"{where}: нет скороговорки недели.")


def audit_twister(r, tw: TongueTwister) -> None:
    from apps.publishing.audit import text_tokens, vocab_until

    where = f"Скороговорка {tw.number}"
    level = tw.week.level
    if tw.number != tw.week.global_number:
        r.errors.append(f"{where}: номер должен быть {tw.week.global_number} (неделя {level.code}-{tw.week.number}).")
    need = TWISTER_SERIES[level.code]
    if tw.series != need:
        r.errors.append(f"{where}: серия {tw.series}, для уровня {level.code} нужна {need}.")
    if tw.source == TongueTwister.Source.FOLK and not tw.source_note.strip():
        r.errors.append(f"{where}: у народной скороговорки нет source_note.")
    if tw.series == TongueTwister.Series.CONNECTED and not tw.full_form.strip():
        r.errors.append(f"{where}: у слияний нет full_form.")
    if tw.series == TongueTwister.Series.SOUNDS:
        stray = _unknown(tw.text, vocab_until(level, tw.week.number))
        if stray:
            r.errors.append(f"{where}: незнакомые слова: {', '.join(stray)}.")
        n = len(text_tokens(tw.text))
        if not 3 <= n <= 8:
            r.errors.append(f"{where}: слов {n}, для серии sounds нужно 3–8.")


def audit_spheres(r) -> None:
    for level in Level.objects.all():
        weeks = list(Week.objects.filter(level=level))
        planned = {w.sphere for w in weeks if w.sphere}
        if not planned:
            continue
        missing = [code for code in SPHERES if code not in planned]
        if not missing:
            continue
        msg = f"{level.code}: в плане нет сфер: {', '.join(missing)}."
        if all(w.sphere for w in weeks):
            r.errors.append(msg)
        else:
            r.warnings.append(msg)


def audit_weeks(r) -> None:
    voices = voices_manifest()
    for scene in WeekScene.objects.select_related("week__level").prefetch_related("chunks"):
        audit_scene(r, scene, voices)
    for tw in TongueTwister.objects.select_related("week__level"):
        audit_twister(r, tw)
    audit_spheres(r)
    audit_lesson_contractions(r)
    for story in Story.objects.filter(is_published=True).exclude(script=[]):
        audit_script(r, f"История {story.number}", story.script, voices, music_required=True,
                     level=story.level, week_number=story.week.number if story.week else 99,
                     warn_spoken=True)


def audit_lesson_contractions(r) -> None:
    for lesson in Lesson.objects.all():
        for i, pair in enumerate(lesson.contractions, 1):
            where = f"{lesson.slug}: «Как сокращают», пара {i}"
            if not any(a in pair.get("short", "") for a in ("'", "’")):
                r.errors.append(f"{where}: в short нет апострофа.")
            if any(a in pair.get("full", "") for a in ("'", "’")):
                r.errors.append(f"{where}: в full не должно быть апострофа.")
