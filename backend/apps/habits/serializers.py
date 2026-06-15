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

    class Meta:
        model = Habit
        fields = [
            "id", "name", "icon", "color", "frequency", "freq_config",
            "goal_type", "goal_value", "goal_unit", "motto",
            "check_in_mode", "auto_increment", "sort_order", "archived",
            "created_at", "reminders", "streak", "max_streak",
        ]
        read_only_fields = ["created_at"]

    def get_streak(self, obj):
        return obj.streak()

    def get_max_streak(self, obj):
        return obj.max_streak()
