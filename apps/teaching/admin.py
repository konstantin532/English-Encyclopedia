from django.contrib import admin
from django.utils import timezone

from .models import CourseIssue, GroupMembership, StudyGroup


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
            kwargs["queryset"] = get_user_model().objects.filter(is_teacher=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)



@admin.register(CourseIssue)
class CourseIssueAdmin(admin.ModelAdmin):
    list_display = ["created_at", "status", "page", "short_comment", "reporter", "reporter_is_teacher"]
    list_filter = ["status", "reporter_is_teacher"]
    search_fields = ["page", "quote", "comment", "reporter__email"]
    readonly_fields = ["reporter", "reporter_is_teacher", "page", "quote", "comment", "created_at", "resolved_at"]
    fields = ["status", "owner_note", "page", "quote", "comment", "reporter", "reporter_is_teacher", "created_at", "resolved_at"]
    actions = ["mark_fixed", "mark_rejected"]

    @admin.display(description="Что не так")
    def short_comment(self, obj):
        return obj.comment[:80]

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        obj.resolved_at = None if obj.status == CourseIssue.Status.OPEN else (obj.resolved_at or timezone.now())
        super().save_model(request, obj, form, change)

    @admin.action(description="Отметить: исправлено")
    def mark_fixed(self, request, queryset):
        queryset.update(status=CourseIssue.Status.FIXED, resolved_at=timezone.now())

    @admin.action(description="Отметить: не ошибка")
    def mark_rejected(self, request, queryset):
        queryset.update(status=CourseIssue.Status.REJECTED, resolved_at=timezone.now())
