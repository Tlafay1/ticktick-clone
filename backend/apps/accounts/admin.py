from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ApiKey, FCMDevice, PushSubscription, User, UserSettings

admin.site.register(User, UserAdmin)
admin.site.register(UserSettings)


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("label", "user", "key", "created_at", "last_used_at")
    readonly_fields = ("key", "created_at", "last_used_at")


admin.site.register(PushSubscription)
admin.site.register(FCMDevice)
