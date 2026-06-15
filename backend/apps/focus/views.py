from django.db.models import Sum
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.views import OwnedModelViewSet
from .models import FocusSession
from .serializers import FocusSessionSerializer


class FocusSessionViewSet(OwnedModelViewSet):
    serializer_class = FocusSessionSerializer

    def get_queryset(self):
        return FocusSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        qs = self.get_queryset().filter(session_type=FocusSession.SessionType.WORK)

        # Distribution par liste
        by_list = {}
        for session in qs.filter(task__isnull=False).select_related("task__project"):
            project = session.task.project
            name = project.name if project else "Inbox"
            by_list[name] = by_list.get(name, 0) + session.duration_seconds

        # Distribution par tag
        by_tag = {}
        for session in qs.filter(task__isnull=False).prefetch_related("task__tags"):
            for tag in session.task.tags.all():
                by_tag[tag.name] = by_tag.get(tag.name, 0) + session.duration_seconds

        total = qs.aggregate(total=Sum("duration_seconds"))["total"] or 0

        return Response({
            "total_seconds": total,
            "by_list": by_list,
            "by_tag": by_tag,
        })
