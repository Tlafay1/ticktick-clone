from rest_framework import serializers

from .models import Project, ProjectGroup, Section


class ProjectGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectGroup
        fields = '__all__'
        read_only_fields = ('user',)


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = '__all__'

    def validate_project(self, project):
        if project.user != self.context["request"].user:
            raise serializers.ValidationError("Liste inconnue.")
        return project


class ProjectSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ('user',)

    def validate_group(self, group):
        if group is not None and group.user != self.context["request"].user:
            raise serializers.ValidationError("Dossier inconnu.")
        return group
