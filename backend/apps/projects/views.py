from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import Q
from .models import ProjectGroup, Project, Section
from .serializers import ProjectGroupSerializer, ProjectSerializer, SectionSerializer
from apps.accounts.models import User


class OwnedModelViewSet(viewsets.ModelViewSet):
    """Base : ne voit et ne modifie que les objets de l'utilisateur connecté."""

    def get_queryset(self):
        if hasattr(self, 'queryset'):
            return self.queryset.filter(user=self.request.user)
        else:
            return self.model.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Set the user to the current authenticated user
        serializer.save(user=self.request.user)


class ProjectGroupViewSet(OwnedModelViewSet):
    serializer_class = ProjectGroupSerializer
    queryset = ProjectGroup.objects.all()


class ProjectViewSet(OwnedModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()

    def get_queryset(self):
        # For smart lists, we might want to filter them differently
        queryset = super().get_queryset()
        
        # If it's a smart list, we might need to apply filters
        # This would be implemented in the API layer or via a custom method
        
        return queryset

    def perform_destroy(self, instance):
        # Soft delete logic could go here if needed
        super().perform_destroy(instance)

    def perform_update(self, serializer):
        # Handle updates for smart list properties
        super().perform_update(serializer)


class SectionViewSet(viewsets.ModelViewSet):
    serializer_class = SectionSerializer
    queryset = Section.objects.all()

    def get_queryset(self):
        return Section.objects.filter(project__user=self.request.user)

    def perform_create(self, serializer):
        # Set the project from the request context
        serializer.save()
