from rest_framework import serializers

from apps.tags.models import Tag
from apps.projects.models import Project

from .models import (
    MAX_SUBTASK_DEPTH, ActivityLog, Attachment, CheckItem, Comment,
    Reminder, SearchHistory, Task, TaskVersion, Template,
)


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ["id", "scope", "name", "data"]
        read_only_fields = []


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = ["id", "task", "trigger_type", "minutes_before", "trigger_at", "annoying"]

    def validate_task(self, task):
        if task.user != self.context["request"].user:
            raise serializers.ValidationError("Tâche inconnue.")
        return task

    def validate(self, data):
        task = data.get("task", getattr(self.instance, "task", None))
        if task:
            count = Reminder.objects.filter(task=task)
            if self.instance:
                count = count.exclude(pk=self.instance.pk)
            if count.count() >= 5:
                raise serializers.ValidationError("Maximum 5 rappels par tâche.")
        return data


class CheckItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckItem
        fields = ["id", "task", "title", "is_done", "completed_at", "sort_order"]
        read_only_fields = ["completed_at"]

    def validate_task(self, task):
        if task.user != self.context["request"].user:
            raise serializers.ValidationError("Tâche inconnue.")
        return task


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "task", "content", "created_at", "edited_at"]
        read_only_fields = ["created_at", "edited_at"]

    def validate_task(self, task):
        if task.user != self.context["request"].user:
            raise serializers.ValidationError("Tâche inconnue.")
        return task


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ["id", "action", "payload", "created_at"]


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        request = self.context.get("request")
        if obj.file:
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None

    class Meta:
        model = Attachment
        fields = ["id", "task", "file", "filename", "content_type", "size",
                  "attachment_type", "url", "created_at"]
        read_only_fields = ["filename", "content_type", "size", "attachment_type", "url", "created_at"]

    def validate_task(self, task):
        if task.user != self.context["request"].user:
            raise serializers.ValidationError("Tâche inconnue.")
        return task


class TaskVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskVersion
        fields = ["id", "task", "description", "created_at"]
        read_only_fields = ["created_at"]


class SearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = ["id", "query", "created_at"]
        read_only_fields = ["created_at"]


class NestedReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = ["id", "trigger_type", "minutes_before", "trigger_at", "annoying"]


class TaskSerializer(serializers.ModelSerializer):
    check_items = CheckItemSerializer(many=True, read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), required=False
    )
    reminders = NestedReminderSerializer(many=True, required=False)
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all(), required=False)


    class Meta:
        model = Task
        fields = [
            "id", "project", "section", "parent", "title", "description",
            "status", "priority", "progress", "is_pinned", "pinned_at",
            "start_date", "due_date", "planned_date", "end_date", "is_all_day", "timezone_name",
            "rrule", "repeat_from", "tags", "sort_order",
            "completed_at", "trashed_at", "archived_at", "created_at", "modified_at",
            "check_items", "reminders", "estimated_pomos",
        ]
        read_only_fields = [
            "completed_at", "trashed_at", "archived_at", "pinned_at", "created_at", "modified_at",
        ]

    def validate_project(self, project):
        if project.user != self.context["request"].user:
            raise serializers.ValidationError("Liste inconnue.")
        return project

    def validate_tags(self, tags):
        user = self.context["request"].user
        for tag in tags:
            if tag.user != user:
                raise serializers.ValidationError(f"Tag inconnu : {tag.name}.")
        return tags

    def validate_section(self, section):
        if section is not None and section.project.user != self.context["request"].user:
            raise serializers.ValidationError("Section inconnue.")
        return section

    def validate_progress(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("La progression va de 0 à 100.")
        return value

    def validate(self, data):
        parent = data.get("parent", getattr(self.instance, "parent", None))
        if parent is not None:
            if parent.user != self.context["request"].user:
                raise serializers.ValidationError({"parent": "Tâche parente inconnue."})
            if self.instance and parent.pk == self.instance.pk:
                raise serializers.ValidationError(
                    {"parent": "Une tâche ne peut pas être sa propre parente."}
                )
            if self.instance:
                # Refuse aussi tout descendant : un cycle ferait boucler à
                # l'infini depth/descendants(). Remontée de la chaîne
                # d'ancêtres du parent proposé, bornée par un ensemble de
                # visités (tolérante à un cycle déjà présent en base).
                node, seen = parent.parent, {parent.pk}
                while node is not None and node.pk not in seen:
                    if node.pk == self.instance.pk:
                        raise serializers.ValidationError(
                            {"parent": "Une tâche ne peut pas devenir la"
                             " sous-tâche d'un de ses descendants."}
                        )
                    seen.add(node.pk)
                    node = node.parent
            if parent.depth + 1 >= MAX_SUBTASK_DEPTH:
                raise serializers.ValidationError(
                    {"parent": f"Imbrication limitée à {MAX_SUBTASK_DEPTH} niveaux."}
                )
            # Une sous-tâche vit dans la liste de son parent.
            data["project"] = parent.project
        # La section doit appartenir à la liste de la tâche.
        section = data.get("section", getattr(self.instance, "section", None))
        project = data.get("project", getattr(self.instance, "project", None))
        if section is not None and project is not None and section.project_id != project.id:
            raise serializers.ValidationError(
                {"section": "La section n'appartient pas à cette liste."}
            )
        # Le flag épinglé maintient pinned_at pour l'ordre d'épinglage.
        return data

    def _save_reminders(self, task, reminders_data):
        task.reminders.all().delete()
        for r in reminders_data[:5]:
            Reminder.objects.create(task=task, **r)

    def update(self, instance, validated_data):
        from django.utils import timezone

        reminders_data = validated_data.pop("reminders", None)
        if "is_pinned" in validated_data:
            if validated_data["is_pinned"] and not instance.is_pinned:
                instance.pinned_at = timezone.now()
            elif not validated_data["is_pinned"]:
                instance.pinned_at = None
        if "description" in validated_data and validated_data["description"] != instance.description:
            TaskVersion.objects.create(task=instance, description=instance.description)
        tracked = {"title", "due_date", "start_date", "priority", "project"}
        changed = sorted(
            f for f, v in validated_data.items()
            if f in tracked and getattr(instance, f) != v
        )
        due_changed = "due_date" in changed
        task = super().update(instance, validated_data)
        if reminders_data is not None:
            self._save_reminders(task, reminders_data)
        if changed:
            ActivityLog.log(task, "updated", fields=changed)
        if due_changed:
            ActivityLog.log(task, "due_date_changed")
        return task

    def create(self, validated_data):
        from django.utils import timezone

        if not validated_data.get("project"):
            validated_data["project"] = Project.objects.get_or_create(
                user=self.context["request"].user, is_inbox=True,
                defaults={"name": "Inbox"},
            )[0]

        reminders_data = validated_data.pop("reminders", None)
        if validated_data.get("is_pinned"):
            validated_data["pinned_at"] = timezone.now()
        task = super().create(validated_data)
        if reminders_data:
            self._save_reminders(task, reminders_data)
        ActivityLog.log(task, "created")
        return task
