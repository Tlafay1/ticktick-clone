from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from .models import Project, ProjectGroup, Section
from .serializers import ProjectGroupSerializer, ProjectSerializer, SectionSerializer


class OwnedModelViewSet(viewsets.ModelViewSet):
    """Base : ne voit et ne modifie que les objets de l'utilisateur connecté."""

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ProjectGroupViewSet(OwnedModelViewSet):
    serializer_class = ProjectGroupSerializer
    queryset = ProjectGroup.objects.all()


class ProjectViewSet(OwnedModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()

    def perform_destroy(self, instance):
        if instance.is_inbox:
            raise ValidationError("L'Inbox ne peut pas être supprimée.")
        super().perform_destroy(instance)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.is_inbox and "name" in serializer.validated_data:
            raise ValidationError("Le nom de l'Inbox ne peut pas être modifié.")
        super().perform_update(serializer)


class SectionViewSet(viewsets.ModelViewSet):
    serializer_class = SectionSerializer
    queryset = Section.objects.all()
    filterset_fields = ["project"]

    def get_queryset(self):
        return Section.objects.filter(project__user=self.request.user)
