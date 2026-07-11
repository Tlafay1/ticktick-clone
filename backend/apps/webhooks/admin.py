from django.contrib import admin

from .models import Webhook, WebhookDelivery


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "url", "is_active", "last_triggered_at")
    list_filter = ("is_active",)


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ("id", "webhook", "event", "status_code", "success", "created_at")
    list_filter = ("success", "event")
