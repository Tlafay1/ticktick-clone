from django.contrib import admin

from .models import ActivityLog, CheckItem, Comment, Task


class CheckItemInline(admin.TabularInline):
    model = CheckItem
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "status", "priority", "due_date", "trashed_at"]
    list_filter = ["status", "priority"]
    search_fields = ["title", "description"]
    inlines = [CheckItemInline]


admin.site.register(Comment)
admin.site.register(ActivityLog)
