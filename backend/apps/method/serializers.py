from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.focus.serializers import FocusSessionSerializer
from apps.projects.models import Project
from apps.tasks.models import Task

from .models import DayLog, MethodConfig, Slot, SlotOccurrence


class MethodConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MethodConfig
        fields = ["level", "jokers_per_month", "today_limit", "review_weekday",
                  "review_time", "pause_until"]

    def validate_review_weekday(self, value):
        if not 0 <= value <= 6:
            raise serializers.ValidationError("Jour de 0 (lundi) à 6 (dimanche).")
        return value

    def validate_level(self, value):
        if value < 1:
            raise serializers.ValidationError("Le niveau commence à 1.")
        return value


class SlotSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Slot
        fields = ["id", "weekday", "start_time", "duration_minutes", "project", "kind",
                  "created_at"]
        read_only_fields = ["created_at"]

    def validate_weekday(self, value):
        if not 0 <= value <= 6:
            raise serializers.ValidationError("Jour de 0 (lundi) à 6 (dimanche).")
        return value

    def validate_duration_minutes(self, value):
        if not 5 <= value <= 240:
            raise serializers.ValidationError("Durée de 5 à 240 minutes.")
        return value

    def validate_project(self, project):
        if project is not None and project.user != self.context["request"].user:
            raise serializers.ValidationError("Liste inconnue.")
        return project


class SlotOccurrenceSerializer(serializers.ModelSerializer):
    end_at = serializers.DateTimeField(read_only=True)
    next_action = serializers.SerializerMethodField()
    focus_session = FocusSessionSerializer(read_only=True)
    task = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = SlotOccurrence
        fields = ["id", "slot", "date", "start_at", "end_at", "duration_minutes", "kind",
                  "status", "excuse_reason", "task", "next_action", "started_at",
                  "focus_session", "recovers"]
        read_only_fields = ["slot", "date", "start_at", "duration_minutes", "kind", "status",
                            "excuse_reason", "started_at", "recovers"]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_next_action(self, obj):
        from .services import next_action

        task = next_action(obj)
        if task is None:
            return None
        return {"id": task.id, "title": task.title, "project": task.project_id}

    def validate_task(self, task):
        if task is not None and task.user != self.context["request"].user:
            raise serializers.ValidationError("Tâche inconnue.")
        return task


class DayColorSerializer(serializers.Serializer):
    color = serializers.ChoiceField(choices=DayLog.Color.choices)
    date = serializers.DateField(required=False)


class ReviewSerializer(serializers.Serializer):
    week = serializers.DateField(required=False)
    level = serializers.IntegerField(required=False, min_value=1)
    amnesty = serializers.BooleanField(required=False, default=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
