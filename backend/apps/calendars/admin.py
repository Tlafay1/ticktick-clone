from django.contrib import admin

from .models import CalendarEvent, CalendarSubscription


@admin.register(CalendarSubscription)
class CalendarSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "url", "is_visible", "last_synced_at")


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("id", "subscription", "title", "start", "is_all_day")
    list_filter = ("is_all_day",)
