from rest_framework import serializers

from .models import CalendarSubscription


class CalendarSubscriptionSerializer(serializers.ModelSerializer):
    is_visible = serializers.BooleanField(default=True, required=False)

    class Meta:
        model = CalendarSubscription
        fields = ["id", "name", "url", "color", "is_visible", "created_at", "last_synced_at"]
        read_only_fields = ["created_at", "last_synced_at"]
