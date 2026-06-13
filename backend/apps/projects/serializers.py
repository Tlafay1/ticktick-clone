from rest_framework import serializers

from .models import Project, ProjectGroup, Section


class ProjectGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectGroup
        fields = ["id", "name", "sort_order", "collapsed"]


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["id", "project", "name", "sort_order", "collapsed"]

    def validate_project(self, project):
        if project.user != self.context["request"].user:
            raise serializers.ValidationError("Projet inconnu.")
        return project


class ProjectSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "group", "name", "color", "icon", "view_mode", "sort_order",
            "is_inbox", "archived", "hidden_from_smart_lists", "sections",
        ]
        read_only_fields = ["is_inbox"]

    def validate_group(self, group):
        if group and group.user != self.context["request"].user:
            raise serializers.ValidationError("Dossier inconnu.")
        return group
