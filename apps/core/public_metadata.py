"""Public URLs use an explicit deployment origin, never the incoming Host header."""

from urllib.parse import urlsplit

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse


def public_origin():
    value = getattr(settings, "PUBLIC_SITE_URL", "").strip()
    try:
        parts = urlsplit(value)
        _ = parts.port  # Validate malformed/out-of-range ports too.
    except ValueError:
        return ""
    if (
        parts.scheme not in {"https", "http"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.path not in {"", "/"}
        or parts.query
        or parts.fragment
    ):
        return ""
    return value.rstrip("/")


def metadata(request):
    namespaces = request.resolver_match.app_names if request.resolver_match else []
    private = any(
        name in {"accounts", "learning", "admin", "api"} for name in namespaces
    ) or bool(request.resolver_match and request.resolver_match.app_name == "teaching"
              and request.resolver_match.url_name != "for_teachers")
    origin = public_origin()
    return {
        "PRIVATE_PAGE": private,
        "PUBLIC_CANONICAL": origin + request.path if origin and not private else "",
    }


def robots(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /learning/",
        "Disallow: /api/",
        "Disallow: /teacher/",
        "Disallow: /group/",
        "Disallow: /healthz/",
    ]
    origin = public_origin()
    if origin:
        lines.append("Sitemap: " + origin + reverse("core:sitemap"))
    return HttpResponse(
        "\n".join(lines) + "\n", content_type="text/plain; charset=utf-8"
    )


def sitemap(request):
    from apps.curriculum.models import Level, Week
    from apps.lessons.models import Lesson
    from apps.lexicon.models import LexicalUnit
    from apps.poems.models import Poem
    from apps.stories.models import Story

    origin = public_origin()
    if not origin:
        raise Http404("Public site origin is not configured")
    if settings.EE_COURSE_LOGIN_REQUIRED:
        # Курс закрыт: поисковикам показываем только открытые страницы.
        from apps.core.access import GUEST_LEVEL, GUEST_WEEK

        paths = [reverse(name) for name in ("core:home", "taxonomy:legend", "teaching:for_teachers")]
        paths += [reverse("curriculum:week", args=[GUEST_LEVEL.lower(), GUEST_WEEK])]
        paths += [reverse("lessons:detail", args=[slug]) for slug in Lesson.objects.filter(
            is_published=True, level__code=GUEST_LEVEL, week__number=GUEST_WEEK).values_list("slug", flat=True)]
        response = render(request, "core/sitemap.xml", {"locations": [origin + path for path in paths]},
                          content_type="application/xml; charset=utf-8")
        response["Cache-Control"] = "public, max-age=300"
        return response
    paths = [
        reverse(name)
        for name in ("core:home", "lexicon:list", "stories:map", "taxonomy:legend")
    ]
    paths += [
        reverse("curriculum:level", args=[slug])
        for slug in (level.slug for level in Level.objects.all())
    ]
    paths += [
        reverse("curriculum:week", args=[week.level.slug, week.number])
        for week in Week.objects.select_related("level")
    ]
    for model, route, field in (
        (Lesson, "lessons:detail", "slug"),
        (Story, "stories:detail", "number"),
        (Poem, "stories:poem", "number"),
    ):
        paths += [
            reverse(route, args=[value])
            for value in model.objects.filter(is_published=True).values_list(
                field, flat=True
            )
        ]
    paths += [
        reverse("lexicon:detail", args=[uid])
        for uid in LexicalUnit.objects.values_list("uid", flat=True)
    ]
    response = render(
        request,
        "core/sitemap.xml",
        {"locations": [origin + path for path in paths]},
        content_type="application/xml; charset=utf-8",
    )
    response["Cache-Control"] = "public, max-age=300"
    return response
