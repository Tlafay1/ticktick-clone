from rest_framework import serializers, viewsets

from .models import Project, ProjectGroup, Section
from .serializers import ProjectGroupSerializer, ProjectSerializer, SectionSerializer


class OwnedModelViewSet(viewsets.ModelViewSet):
    """Base : ne voit et ne modifie que les objets de l'utilisateur connecté."""

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ProjectGroupViewSet(OwnedModelViewSet):
    queryset = ProjectGroup.objects.all()
    serializer_class = ProjectGroupSerializer


class ProjectViewSet(OwnedModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filterset_fields = ["archived", "group"]

    def perform_destroy(self, instance):
        if instance.is_inbox:
            raise serializers.ValidationError(
                {"detail": "L'Inbox ne peut pas être supprimée."}
            )
        instance.delete()

    def perform_update(self, serializer):
        if serializer.instance.is_inbox and "name" in serializer.validated_data:
            raise serializers.ValidationError(
                {"detail": "L'Inbox ne peut pas être renommée."}
            )
        serializer.save()


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    filterset_fields = ["project"]

    def get_queryset(self):
        return self.queryset.filter(project__user=self.request.user)
