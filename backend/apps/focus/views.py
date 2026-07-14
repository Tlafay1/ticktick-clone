import django_filters
from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.actors import get_actor
from apps.projects.views import OwnedModelViewSet
from .models import FocusSession
from .serializers import FocusSessionSerializer


class FocusSessionFilter(django_filters.FilterSet):
    start_after = django_filters.IsoDateTimeFilter(field_name="start_at", lookup_expr="gte")
    start_before = django_filters.IsoDateTimeFilter(field_name="start_at", lookup_expr="lt")

    class Meta:
        model = FocusSession
        fields = ["mode", "session_type", "task"]


class FocusSessionViewSet(OwnedModelViewSet):
    serializer_class = FocusSessionSerializer
    filterset_class = FocusSessionFilter

    def get_queryset(self):
        return FocusSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _running(self):
        return self.get_queryset().filter(end_at__isnull=True).first()

    def _emit(self, event, session):
        from apps.webhooks.dispatch import emit

        emit(self.request.user, event, FocusSessionSerializer(session).data,
             actor=get_actor(self.request))

    @extend_schema(request=OpenApiTypes.OBJECT, responses=FocusSessionSerializer)
    @action(detail=False, methods=["post"])
    def start(self, request):
        """Démarre une session de focus pilotée serveur.

        409 si une session est déjà en cours. Corps optionnel :
        planned_seconds, task, mode, session_type. Émet `pomodoro.started`.
        """
        if self._running() is not None:
            return Response({"detail": "Une session est déjà en cours."},
                            status=status.HTTP_409_CONFLICT)
        task = None
        task_id = request.data.get("task")
        if task_id is not None:
            from apps.tasks.models import Task

            task = Task.objects.filter(pk=task_id, user=request.user).first()
            if task is None:
                return Response({"detail": "Tâche inconnue."},
                                status=status.HTTP_400_BAD_REQUEST)
        session = FocusSession.objects.create(
            user=request.user,
            task=task,
            mode=request.data.get("mode", FocusSession.Mode.POMODORO),
            session_type=request.data.get("session_type", FocusSession.SessionType.WORK),
            planned_seconds=request.data.get("planned_seconds"),
            start_at=timezone.now(),
        )
        self._emit("pomodoro.started", session)
        return Response(FocusSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses=FocusSessionSerializer)
    @action(detail=False, methods=["post"])
    def stop(self, request):
        """Clôt la session en cours (409 si aucune).

        Calcule `duration_seconds`. Émet `pomodoro.completed` si la durée
        prévue est atteinte (ou si aucune n'était fixée), sinon
        `pomodoro.stopped`.
        """
        session = self._running()
        if session is None:
            return Response({"detail": "Aucune session en cours."},
                            status=status.HTTP_409_CONFLICT)
        now = timezone.now()
        session.end_at = now
        session.duration_seconds = int((now - session.start_at).total_seconds())
        session.save(update_fields=["end_at", "duration_seconds"])
        completed = (
            session.planned_seconds is None
            or session.duration_seconds >= session.planned_seconds
        )
        self._emit("pomodoro.completed" if completed else "pomodoro.stopped", session)
        return Response(FocusSessionSerializer(session).data)

    @extend_schema(responses=FocusSessionSerializer)
    @action(detail=False, methods=["get"])
    def current(self, request):
        """Session en cours (200) ou 204 si aucune."""
        session = self._running()
        if session is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(FocusSessionSerializer(session).data)

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
