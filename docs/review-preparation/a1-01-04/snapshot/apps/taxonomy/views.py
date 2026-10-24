from django.shortcuts import render

from .models import PartOfSpeech
from .registry import PALETTE


def legend(request):
    return render(request, "taxonomy/legend.html", {
        "categories": PartOfSpeech.objects.prefetch_related("classes"),
        "palette": [(n, name, hex_) for n, (name, hex_) in PALETTE.items()],
    })
