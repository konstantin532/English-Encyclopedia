import re
from pathlib import Path

import yaml
from django.conf import settings
from django.db.models import Prefetch

from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.curriculum.models import Level
from apps.publishing.audit import text_tokens
from apps.poems.models import Poem
from apps.taxonomy.markup import strip_markup
from apps.taxonomy.models import PartOfSpeech

from .models import Story
from .script import build_lines


def course_map(request):
    levels = []
    level_rows = Level.objects.prefetch_related(
        Prefetch("stories", queryset=Story.objects.select_related("week").filter(is_published=True)),
        Prefetch("poems", queryset=Poem.objects.select_related("week").filter(is_published=True)),
    )
    for lv in level_rows:
        levels.append({
            "level": lv,
            "stories": lv.stories.all(),
            "poems": lv.poems.all(),
        })
    return render(request, "stories/map.html", {"levels": levels})


# Обложки историй «Атласа живого языка»: только для тех, где картинка уже есть.
STORY_COVERS = {
    1: "Анна и Том открывают коробку, а в ней сидит рыжий кот",
    2: "Анна и Мия в кафе на углу, рыжий кот сидит на стуле",
    3: "Том пробует старинный ключ у почтового ящика",
    4: "Анна и Том читают письмо без имени, рядом кот",
    5: "Анна и Том нашли за шкафом большую семейную фотографию",
}


def story_cover(number):
    alt = STORY_COVERS.get(number)
    return {"src": static(f"img/atlas/s{number:02d}-1536.webp"), "alt": alt} if alt else None


def story_detail(request, number):
    story = get_object_or_404(Story.objects.select_related("level", "week"), number=number, is_published=True)
    paragraphs = [p for p in story.body.split("\n\n") if p.strip()]
    lines, speakers = build_lines(story.script)
    return render(request, "stories/detail.html", {
        "story": story,
        "cover": story_cover(story.number),
        "paragraphs": paragraphs,
        "lines": lines,
        "speakers": speakers,
        "audio": story.audio or None,
        "new_units": story.new_units.select_related("semantic_class__category"),
        "focus": PartOfSpeech.objects.filter(code__in=list(story.focus)),
        "word_count": len(text_tokens(story.body)),
    })


@ensure_csrf_cookie
def poem_detail(request, number):
    poem = get_object_or_404(Poem.objects.select_related("level", "week"), number=number, is_published=True)
    # Пустая строка в body разделяет строфы; номера строк в gaps и pronunciation считают только строки текста.
    lines, stanza_starts = [], set()
    for raw in poem.body.strip().splitlines():
        if not raw.strip():
            stanza_starts.add(len(lines))
            continue
        lines.append(raw)
    gapped = []
    for i, line in enumerate(lines, start=1):
        text = strip_markup(line)
        gap_index = next((k for k, g in enumerate(poem.gaps) if g["line"] == i), None)
        row = {"before": text, "gap": None, "stanza": (i - 1) in stanza_starts}
        if gap_index is not None:
            m = re.search(rf"\b{re.escape(poem.gaps[gap_index]['word'])}\b", text, re.I)
            if m:
                row.update(before=text[: m.start()], after=text[m.end():], gap=gap_index)
        gapped.append(row)
    pron = poem.pronunciation or []
    rows = [{"line": line, "pr": pron[k] if k < len(pron) else None, "stanza": k in stanza_starts}
            for k, line in enumerate(lines)]
    return render(request, "poems/detail.html", {
        "poem": poem,
        "rows": rows,
        "gapped": gapped,
        "targets": poem.target_units.select_related("semantic_class__category"),
    })
