from django.utils import timezone
from rest_framework import serializers

from .models import Habit, HabitCheckIn, HabitReminder


class HabitReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitReminder
        fields = ["id", "time"]


class HabitCheckInSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitCheckIn
        fields = ["id", "date", "quantity", "note", "completed", "created_at"]
        read_only_fields = ["created_at"]


class HabitSerializer(serializers.ModelSerializer):
    reminders = HabitReminderSerializer(many=True, read_only=True)
    streak = serializers.SerializerMethodField()
    max_streak = serializers.SerializerMethodField()
    # Pour la programmation locale des rappels (Android) : « aujourd'hui » au sens
    # du fuseau de l'utilisateur, comme le dispatch serveur.
    due_today = serializers.SerializerMethodField()
    completed_today = serializers.SerializerMethodField()

    class Meta:
        model = Habit
        fields = [
            "id", "name", "icon", "color", "frequency", "freq_config",
            "goal_type", "goal_value", "goal_unit", "motto",
            "check_in_mode", "auto_increment", "sort_order", "archived",
            "created_at", "reminders", "streak", "max_streak",
            "due_today", "completed_today",
        ]
        read_only_fields = ["created_at"]

    def _today(self):
        # Mémorisé : en liste, le même sérialiseur enfant sert toutes les habitudes.
        if not hasattr(self, "_today_cache"):
            from apps.accounts.models import UserSettings

            user = self.context["request"].user
            user_settings, _ = UserSettings.objects.get_or_create(user=user)
            self._today_cache = timezone.now().astimezone(user_settings.tzinfo).date()
        return self._today_cache

    def get_due_today(self, obj):
        from .tasks import _due_today

        return _due_today(obj, self._today())

    def get_completed_today(self, obj):
        today = self._today()
        return any(c.date == today and c.completed for c in obj.checkins.all())

    def get_streak(self, obj):
        return obj.streak()

    def get_max_streak(self, obj):
        return obj.max_streak()
