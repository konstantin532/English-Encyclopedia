"""Права ученика на свои данные: скачать всё и удалить аккаунт со всей историей."""
import json

from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

PROFILE_FIELDS = ("email", "display_name", "current_level_id", "date_joined", "last_login", "markers_in_color")
# Чужие оценки (например, кто из преподавателей проверил ответ) не раскрываем.
HIDDEN_FIELDS = {"reviewed_by"}


def learner_relations():
    """Все таблицы, где строки принадлежат ученику (внешний ключ на пользователя)."""
    User = get_user_model()
    for rel in User._meta.related_objects:
        if rel.one_to_many and rel.field.remote_field.on_delete.__name__ == "CASCADE":
            yield rel


def export_data(user) -> dict:
    data = {
        "exported_at": timezone.now(),
        "profile": {f: getattr(user, f, None) for f in PROFILE_FIELDS},
        "tables": {},
    }
    for rel in learner_relations():
        model = rel.related_model
        names = [f.attname for f in model._meta.concrete_fields
                 if f.attname != rel.field.attname and f.name not in HIDDEN_FIELDS]
        rows = list(model._default_manager.filter(**{rel.field.name: user}).values(*names))
        data["tables"][f"{model._meta.app_label}.{model._meta.model_name}"] = rows
    return data


@login_required
def download_my_data(request):
    body = json.dumps(export_data(request.user), cls=DjangoJSONEncoder, ensure_ascii=False, indent=2)
    response = HttpResponse(body, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="english-encyclopedia-my-data.json"'
    response["Cache-Control"] = "no-store"
    return response


@login_required
@require_http_methods(["GET", "POST"])
def delete_account(request):
    error = ""
    if request.method == "POST":
        if request.POST.get("confirm") != "УДАЛИТЬ":
            error = "Впишите слово УДАЛИТЬ, чтобы подтвердить."
        elif not request.user.check_password(request.POST.get("password", "")):
            error = "Неверный пароль."
        else:
            user = request.user
            logout(request)
            with transaction.atomic():
                user.delete()  # каскадом удаляются прогресс, ответы, повторения и цели ученика
            return render(request, "accounts/delete_account.html", {"deleted": True})
    return render(request, "accounts/delete_account.html", {"error": error}, status=400 if error else 200)
