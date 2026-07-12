from rest_framework import serializers

from .models import CalendarEvent, CalendarSubscription


class CalendarSubscriptionSerializer(serializers.ModelSerializer):
    is_visible = serializers.BooleanField(default=True, required=False)

    class Meta:
        model = CalendarSubscription
        fields = ["id", "name", "url", "color", "is_visible", "created_at", "last_synced_at"]
        read_only_fields = ["created_at", "last_synced_at"]


class CalendarEventSerializer(serializers.ModelSerializer):
    color = serializers.CharField(source="subscription.color", read_only=True)
    calendar_name = serializers.CharField(source="subscription.name", read_only=True)

    class Meta:
        model = CalendarEvent
        fields = [
            "id", "subscription", "calendar_name", "color",
            "uid", "title", "location", "start", "end", "is_all_day",
        ]
