"""Отдельная интерактивная лаборатория A1: не меняет действующий учебный контент."""
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def cafe_lab(request):
    """Интерактивный пилот недели 3 без записи ответов/аудио в базу."""
    return render(request, "core/cafe_lab.html")
