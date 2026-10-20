"""«Классика»: легендарные скороговорки и стихи. Культурный бонус к курсу, не основа программы."""
from functools import lru_cache

import yaml
from django.conf import settings
from django.shortcuts import render

# Свободны от авторских прав в США только тексты, опубликованные до 1929 года.
PUBLIC_DOMAIN_BEFORE = 1929


@lru_cache(maxsize=1)
def classics() -> dict:
    path = settings.CONTENT_DIR / "manifests" / "classics.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for poem in data.get("poems", []):
        if poem["year"] >= PUBLIC_DOMAIN_BEFORE:
            raise ValueError(f"{poem['slug']}: опубликовано в {poem['year']}, это не общественное достояние")
    return data


def classics_page(request):
    data = classics()
    return render(request, "core/classics.html", {"twisters": data["twisters"], "poems": data["poems"]})
