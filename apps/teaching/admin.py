from django.contrib import admin

from .models import GroupMembership, StudyGroup


class MembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 0
    autocomplete_fields = ["student"]
    readonly_fields = ["joined_at"]


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "teacher", "join_code", "is_open", "size"]
    list_filter = ["is_open", "teacher"]
    search_fields = ["name", "join_code", "teacher__email", "teacher__display_name"]
    readonly_fields = ["join_code", "created_at"]
    autocomplete_fields = ["teacher"]
    inlines = [MembershipInline]

    @admin.display(description="Учеников")
    def size(self, obj):
        return obj.memberships.count()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "teacher":
            from django.contrib.auth import get_user_model
            from django.db.models import Q
            # Те же, кто может вести группы в кабинете (apps/teaching/access.can_teach).
            kwargs["queryset"] = get_user_model().objects.filter(Q(is_teacher=True) | Q(is_superuser=True))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
