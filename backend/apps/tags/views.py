from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.views import OwnedModelViewSet

from .models import Tag
from .serializers import TagSerializer


class TagViewSet(OwnedModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filterset_fields = ["parent"]

    @action(detail=True, methods=["post"])
    def merge(self, request, pk=None):
        """Fusionne ce tag dans le tag cible : POST {"target": <id>}."""
        source = self.get_object()
        try:
            target = self.get_queryset().get(pk=request.data.get("target"))
        except Tag.DoesNotExist:
            return Response(
                {"detail": "Tag cible inconnu."}, status=status.HTTP_400_BAD_REQUEST
            )
        if target == source:
            return Response(
                {"detail": "Impossible de fusionner un tag avec lui-même."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        source.merge_into(target)
        return Response(TagSerializer(target).data)
