from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count, Q
from django.utils.html import format_html
from django.utils import timezone

from .models import User


class StudioRoleFilter(admin.SimpleListFilter):
    title = "роль"
    parameter_name = "role"

    def lookups(self, request, model_admin):
        return (("learners", "Ученики"), ("editors", "Команда"), ("admins", "Администраторы"))

    def queryset(self, request, queryset):
        if self.value() == "learners":
            return queryset.filter(is_staff=False, is_superuser=False)
        if self.value() == "editors":
            return queryset.filter(is_staff=True, is_superuser=False)
        if self.value() == "admins":
            return queryset.filter(is_superuser=True)
        return queryset


@admin.register(User)
class EmailUserAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["person", "role_badge", "learning_level", "status_badge", "last_seen"]
    list_display_links = ["person"]
    list_select_related = ["current_level"]
    list_per_page = 25
    list_filter = [StudioRoleFilter, "is_active", "current_level", "groups"]
    search_fields = ["email", "display_name"]
    search_help_text = "Поиск по имени или электронной почте"
    change_list_template = "admin/accounts/user/change_list.html"
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        ("Учётная запись", {"fields": ("email", "password"), "description": "Электронная почта используется для входа на платформу."}),
        ("Профиль и обучение", {"fields": ("display_name", "current_level", "markers_enabled", "markers_in_color")}),
        ("Доступ к платформе", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"), "classes": ("collapse",), "description": "Права определяют, какие разделы доступны пользователю."}),
        ("История аккаунта", {"fields": ("date_joined", "last_login"), "classes": ("collapse",)}),
    )
    add_fieldsets = (("Новый пользователь", {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)

    @admin.display(description="Пользователь", ordering="email")
    def person(self, obj):
        name = obj.display_name.strip() or obj.email.split("@")[0]
        words = name.split()
        initials = "".join(word[0] for word in words[:2]).upper() if len(words) > 1 else name[:2].upper()
        return format_html('<span class="studio-person"><span class="studio-avatar" aria-hidden="true">{}</span><span class="studio-person-copy"><strong>{}</strong><small>{}</small></span></span>', initials, name, obj.email)

    @admin.display(description="Роль", ordering="is_superuser")
    def role_badge(self, obj):
        if obj.is_superuser:
            tone, label = "owner", "Администратор"
        elif obj.is_staff:
            tone, label = "editor", "Команда"
        else:
            tone, label = "learner", "Ученик"
        return format_html('<span class="studio-badge studio-badge-{}">{}</span>', tone, label)

    @admin.display(description="Уровень", ordering="current_level__order")
    def learning_level(self, obj):
        return str(obj.current_level) if obj.current_level else "Не выбран"

    @admin.display(description="Статус", ordering="is_active")
    def status_badge(self, obj):
        return format_html('<span class="studio-status studio-status-{}"><span aria-hidden="true"></span>{}</span>', "active" if obj.is_active else "inactive", "Активен" if obj.is_active else "Отключён")

    @admin.display(description="Последний вход", ordering="last_login")
    def last_seen(self, obj):
        return timezone.localtime(obj.last_login).strftime("%d.%m.%Y · %H:%M") if obj.last_login else "Ещё не входил"

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        if hasattr(response, "context_data") and response.context_data and "cl" in response.context_data:
            cl = response.context_data["cl"]
            response.context_data["studio_user_stats"] = cl.queryset.aggregate(total=Count("pk"), active=Count("pk", filter=Q(is_active=True)), team=Count("pk", filter=Q(is_staff=True) | Q(is_superuser=True)))
            current = request.GET.get("role", "")
            response.context_data["studio_role_tabs"] = [
                {"label": label, "url": cl.get_query_string({"role": value or None}, remove=["p"]), "selected": current == value}
                for value, label in (("", "Все пользователи"), ("learners", "Ученики"), ("editors", "Команда"), ("admins", "Администраторы"))
            ]
        return response

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        labels = {"email": "Электронная почта", "display_name": "Имя для обращения", "current_level": "Уровень английского", "markers_enabled": "Маркеры в тексте", "markers_in_color": "Цветная разметка частей речи"}
        for name, label in labels.items():
            if name in form.base_fields:
                form.base_fields[name].label = label
        return form
