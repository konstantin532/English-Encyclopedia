from django.shortcuts import get_object_or_404, render

from apps.curriculum.models import Level
from apps.taxonomy.models import PartOfSpeech

from .models import LexicalUnit


def unit_list(request):
    units = LexicalUnit.objects.select_related("part_of_speech", "semantic_class__category", "internal_level")
    level = request.GET.get("level")
    cat = request.GET.get("cat")
    query = request.GET.get("q", "").strip()[:200]
    if query:
        units = units.filter(search_text__contains=query.casefold())
    if level:
        units = units.filter(internal_level__code=level)
    if cat:
        units = units.filter(part_of_speech__code=cat)
    return render(request, "lexicon/list.html", {
        "units": units, "levels": Level.objects.all(), "categories": PartOfSpeech.objects.all(),
        "active_level": level, "active_cat": cat, "search_query": query,
    })


def unit_detail(request, uid):
    unit = get_object_or_404(
        LexicalUnit.objects.select_related("part_of_speech", "semantic_class__category", "internal_level"), uid=uid
    )
    return render(request, "lexicon/detail.html", {"unit": unit, "lessons": unit.lessons.all()})
