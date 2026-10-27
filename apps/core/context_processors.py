from django.utils import timezone
from django.conf import settings


def site(request):
    user = getattr(request, "user", None)
    authed = bool(user and user.is_authenticated)
    due = 0
    if authed:
        from apps.learning.models import UnitProgress

        due = UnitProgress.objects.filter(user=user, next_review_at__lte=timezone.now()).count()
    return {"trainer_enabled": getattr(settings, "EE_VOCABULARY_TRAINER_ENABLED", False),
            "phrases_enabled": getattr(settings, "EE_PHRASE_MEMORY_ENABLED", False), "SITE_NAME": "English Encyclopedia", "MARKERS_MONO": authed and not user.markers_in_color, "REVIEW_DUE": due}
