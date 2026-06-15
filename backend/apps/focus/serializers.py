from rest_framework import serializers
from .models import FocusSession


class FocusSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusSession
        fields = ["id", "task", "mode", "session_type", "start_at", "end_at", "duration_seconds"]
