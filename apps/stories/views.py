import re
from pathlib import Path

import yaml
from django.conf import settings

from django.shortcuts import get_object_or_404, render
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
    for lv in Level.objects.all():
        levels.append({
            "level": lv,
            "stories": Story.objects.filter(level=lv).select_related("week"),
            "poems": Poem.objects.filter(level=lv).select_related("week"),
        })
    return render(request, "stories/map.html", {"levels": levels})


def story_detail(request, number):
    story = get_object_or_404(Story.objects.select_related("level", "week"), number=number, is_published=True)
    paragraphs = [p for p in story.body.split("\n\n") if p.strip()]
    lines, speakers = build_lines(story.script)
    return render(request, "stories/detail.html", {
        "story": story,
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
    lines = poem.body.strip().splitlines()
    gapped = []
    for i, line in enumerate(lines, start=1):
        text = strip_markup(line)
        gap_index = next((k for k, g in enumerate(poem.gaps) if g["line"] == i), None)
        if gap_index is None:
            gapped.append({"before": text, "gap": None})
            continue
        m = re.search(rf"\b{re.escape(poem.gaps[gap_index]['word'])}\b", text, re.I)
        gapped.append({"before": text[: m.start()], "after": text[m.end():], "gap": gap_index} if m
                      else {"before": text, "gap": None})
    return render(request, "poems/detail.html", {
        "poem": poem,
        "rows": list(zip(lines, poem.pronunciation)) if poem.pronunciation else [(l, None) for l in lines],
        "gapped": gapped,
        "targets": poem.target_units.select_related("semantic_class__category"),
    })
