from rest_framework import serializers
from .models import Countdown


class CountdownSerializer(serializers.ModelSerializer):
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Countdown
        fields = ["id", "title", "target_date", "description", "pinned", "created_at", "days_remaining"]
        read_only_fields = ["created_at"]

    def get_days_remaining(self, obj):
        return obj.days_remaining()
