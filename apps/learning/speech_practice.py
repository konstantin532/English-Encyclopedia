"""Речевое интервальное повторение: самооценка, только метаданные, без голоса."""
import json
import re

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.core.a1_active import active_topics
from apps.curriculum.models import TongueTwister
from apps.lessons.models import Lesson
from apps.poems.models import Poem

from .models import SpeechPracticeProgress


KEY_PATTERN = re.compile(r"^(?:lesson:[a-z0-9_-]{1,80}|twister:[1-9][0-9]{0,2}|poem:[1-9][0-9]{0,2})$")
MAX_SPEECH_PAYLOAD_BYTES = 16_384


def content_details(key):
    """Возвращает границы существующего опубликованного контента, не доверяя индексу браузера."""
    if not isinstance(key, str) or not KEY_PATTERN.fullmatch(key):
        return None
    kind, name = key.split(":", 1)
    if kind == "lesson":
        lesson = Lesson.objects.select_related("level").filter(slug=name, is_published=True, level__code="A1").first()
        if not lesson:
            return None
        topic = active_topics().get(lesson.order)
        if not topic or topic["slug"] != lesson.slug:
            return None
        return {"count": len(topic["missions"]), "title": lesson.title,
                "url": reverse("lessons:detail", args=[lesson.slug]) + "#spoken-coach"}
    if kind == "twister":
        twister = TongueTwister.objects.select_related("week__level").filter(number=int(name)).first()
        if not twister:
            return None
        week = twister.week
        return {"count": len(twister.warmup) + 1 + bool(twister.target_line),
                "title": "Скороговорка недели " + str(week.number),
                "url": reverse("curriculum:week", args=[week.level.slug, week.number]) + "#twister"}
    poem = Poem.objects.filter(number=int(name), is_published=True).first()
    if not poem:
        return None
    return {"count": len([line for line in poem.body.splitlines() if line.strip()]),
            "title": poem.title,
            "url": reverse("stories:poem", args=[poem.number]) + "#speech-studio"}


@login_required
@require_http_methods(["GET", "POST"])
def speech_practice_api(request):
    if request.method == "POST":
        # Bound parsing cost just like other JSON learning endpoints.
        if len(request.body) > MAX_SPEECH_PAYLOAD_BYTES:
            return HttpResponseBadRequest("Слишком большой запрос")
        try:
            payload = json.loads(request.body)
        except (ValueError, UnicodeDecodeError, RecursionError):
            return HttpResponseBadRequest("Неверный формат данных")
        if not isinstance(payload, dict):
            return HttpResponseBadRequest("Ожидается объект")
        key = payload.get("key")
        index = payload.get("index")
        rating = payload.get("rating")
        if rating not in SpeechPracticeProgress.Result.values or type(index) is not int:
            return HttpResponseBadRequest("Неверная оценка или фрагмент")
        details = content_details(key)
        if not details or index < 0 or index >= details["count"]:
            return HttpResponseBadRequest("Такого фрагмента нет")
        now = timezone.now()
        with transaction.atomic():
            progress, _ = SpeechPracticeProgress.objects.select_for_update().get_or_create(
                user=request.user, content_key=key, fragment=index,
            )
            progress.register(rating, now=now)
            progress.save(update_fields=["stage", "attempts", "result", "next_review_at", "updated_at"])
        return JsonResponse({"index": index, "rating": progress.result, "stage": progress.stage,
                             "attempts": progress.attempts, "next_review_at": progress.next_review_at.isoformat(),
                             "due": progress.next_review_at <= now,
                             "note": "Результат основан только на вашей самооценке, а не проверке микрофона."})
    key = request.GET.get("key", "")
    details = content_details(key)
    if not details:
        return HttpResponseBadRequest("Неизвестное произведение")
    progress = SpeechPracticeProgress.objects.filter(user=request.user, content_key=key).order_by("fragment")
    return JsonResponse({
        "key": key, "count": details["count"],
        "items": [
            {"index": p.fragment, "rating": p.result, "stage": p.stage, "attempts": p.attempts,
             "next_review_at": p.next_review_at.isoformat(), "due": p.next_review_at <= timezone.now()}
            for p in progress if p.fragment < details["count"]
        ],
    })


def published_speech_catalog():
    """Current learner-facing speech targets in three bulk database queries.

    No persistent cache: a newly unpublished lesson must stop appearing
    immediately, while old progress records remain available in the DB.
    """
    result = {}
    topics = active_topics()
    for lesson in Lesson.objects.filter(
        is_published=True, level__code="A1",
    ).values("slug", "order", "title"):
        topic = topics.get(lesson["order"])
        if topic and topic["slug"] == lesson["slug"]:
            result["lesson:" + lesson["slug"]] = {
                "count": len(topic["missions"]), "title": lesson["title"],
                "url": reverse("lessons:detail", args=[lesson["slug"]]) + "#spoken-coach",
            }
    for twister in TongueTwister.objects.select_related("week__level").all():
        result["twister:" + str(twister.number)] = {
            "count": len(twister.warmup) + 1 + bool(twister.target_line),
            "title": "Скороговорка недели " + str(twister.week.number),
            "url": reverse(
                "curriculum:week", args=[twister.week.level.slug, twister.week.number],
            ) + "#twister",
        }
    for poem in Poem.objects.filter(is_published=True).values("number", "body", "title"):
        result["poem:" + str(poem["number"])] = {
            "count": sum(bool(line.strip()) for line in poem["body"].splitlines()),
            "title": poem["title"],
            "url": reverse("stories:poem", args=[poem["number"]]) + "#speech-studio",
        }
    return result


def valid_due_speech_items(user, now=None, limit=None):
    """Yield published, existing review fragments, caching content by key.

    Reuse this selection for the dashboard badge and the visible queue.
    """
    now = now or timezone.now()
    due = (SpeechPracticeProgress.objects.filter(user=user, next_review_at__lte=now)
           .order_by("next_review_at", "pk"))
    catalog = None
    yielded = 0
    for item in due.iterator(chunk_size=200):
        if catalog is None:
            catalog = published_speech_catalog()
        details = catalog.get(item.content_key)
        if not details or item.fragment >= details["count"]:
            continue
        yield item, details
        yielded += 1
        if limit is not None and yielded >= limit:
            break


@login_required
def speech_review(request):
    now = timezone.now()
    pending = []
    for item, details in valid_due_speech_items(request.user, now=now, limit=100):
        url, hashmark, anchor = details["url"].partition("#")
        pending.append({
            "title": details["title"], "fragment": item.fragment + 1,
            "rating": item.get_result_display(),
            "url": url + "?speech=" + str(item.fragment) + ("#" + anchor if hashmark else ""),
            "content_key": item.content_key,
        })
    upcoming = SpeechPracticeProgress.objects.filter(user=request.user, next_review_at__gt=now).order_by("next_review_at").first()
    return render(request, "learning/speech_review.html", {
        "pending": pending,
        "upcoming": upcoming,
    })
