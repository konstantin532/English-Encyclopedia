from django.utils import timezone


def site(request):
    user = getattr(request, "user", None)
    authed = bool(user and user.is_authenticated)
    due = 0
    if authed:
        from apps.learning.models import UnitProgress

        due = UnitProgress.objects.filter(user=user, next_review_at__lte=timezone.now()).count()
    return {"SITE_NAME": "English Encyclopedia", "MARKERS_MONO": authed and not user.markers_in_color, "REVIEW_DUE": due}
