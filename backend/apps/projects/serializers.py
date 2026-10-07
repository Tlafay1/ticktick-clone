from rest_framework import serializers

from .models import MAX_ACTIVE_OBJECTIVES, Objective, Project, ProjectGroup, Section


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
    # M38.2 : progression (terminées / terminées + ouvertes), hors propositions.
    tasks_total = serializers.SerializerMethodField()
    tasks_done = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ('user',)

    def _counts(self, obj):
        # Annotés par ProjectViewSet en liste ; calculés à l'unité sinon.
        if hasattr(obj, "n_done"):
            return obj.n_done, obj.n_open
        from apps.tasks.models import Task

        qs = obj.tasks.filter(trashed_at__isnull=True, archived_at__isnull=True, proposed=False)
        return (qs.filter(status=Task.Status.COMPLETED).count(),
                qs.filter(status=Task.Status.NORMAL).count())

    def get_tasks_total(self, obj):
        done, open_ = self._counts(obj)
        return done + open_

    def get_tasks_done(self, obj):
        return self._counts(obj)[0]

    def validate_objective(self, value):
        if value == Objective.ACTIVE:
            others = Project.objects.filter(
                user=self.context["request"].user, objective=Objective.ACTIVE,
            )
            if self.instance is not None:
                others = others.exclude(pk=self.instance.pk)
            if others.count() >= MAX_ACTIVE_OBJECTIVES:
                raise serializers.ValidationError(
                    f"{MAX_ACTIVE_OBJECTIVES} objectifs actifs au plus : "
                    "range d'abord un objectif au frigo."
                )
        return value

    def validate_group(self, group):
        if group is not None and group.user != self.context["request"].user:
            raise serializers.ValidationError("Dossier inconnu.")
        return group
