from django.core.paginator import Paginator
from django.conf import settings
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
    page_obj = Paginator(units, 48).get_page(request.GET.get("page"))
    if getattr(settings, "EE_VOCABULARY_TRAINER_ENABLED", False) and request.user.is_authenticated:
        from apps.learning.trainer_service import register_legacy_exposure
        # Evaluate only the rendered page, never the entire filtered queryset.
        register_legacy_exposure(request.user, page_obj)
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "lexicon/list.html", {
        "units": page_obj, "page_obj": page_obj,
        "total_units": page_obj.paginator.count, "querystring": params.urlencode(), "levels": Level.objects.all(), "categories": PartOfSpeech.objects.all(),
        "active_level": level, "active_cat": cat, "search_query": query,
    })


def unit_detail(request, uid):
    unit = get_object_or_404(
        LexicalUnit.objects.select_related("part_of_speech", "semantic_class__category", "internal_level"), uid=uid
    )
    trainer_entry = (getattr(settings, "EE_VOCABULARY_TRAINER_ENABLED", False)
                     and request.user.is_authenticated and uid in ("LX-00055", "LX-00285", "LX-00084"))
    if trainer_entry:
        from apps.learning.trainer_service import register_legacy_exposure
        register_legacy_exposure(request.user, [unit])
    return render(request, "lexicon/detail.html", {"unit": unit, "lessons": unit.lessons.all(),
                                                  "trainer_entry": trainer_entry})
