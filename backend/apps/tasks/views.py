import django_filters
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.views import OwnedModelViewSet

from .models import CheckItem, Comment, Reminder, Task, Template
from .serializers import (
    ActivityLogSerializer,
    CheckItemSerializer,
    CommentSerializer,
    ReminderSerializer,
    TaskSerializer,
    TemplateSerializer,
)


class TaskFilter(django_filters.FilterSet):
    due_before = django_filters.IsoDateTimeFilter(field_name="due_date", lookup_expr="lt")
    due_after = django_filters.IsoDateTimeFilter(field_name="due_date", lookup_expr="gte")
    completed_before = django_filters.IsoDateTimeFilter(
        field_name="completed_at", lookup_expr="lt"
    )
    completed_after = django_filters.IsoDateTimeFilter(
        field_name="completed_at", lookup_expr="gte"
    )
    has_date = django_filters.BooleanFilter(
        field_name="due_date", lookup_expr="isnull", exclude=True
    )
    tag = django_filters.CharFilter(field_name="tags__name")
    parent_isnull = django_filters.BooleanFilter(field_name="parent", lookup_expr="isnull")

    class Meta:
        model = Task
        fields = ["project", "section", "parent", "status", "priority", "is_pinned"]


class TaskViewSet(OwnedModelViewSet):
    queryset = Task.objects.all().prefetch_related("check_items", "tags")
    serializer_class = TaskSerializer
    filterset_class = TaskFilter
    ordering_fields = ["sort_order", "due_date", "priority", "created_at", "title",
                       "completed_at", "modified_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        # Sur le listing seulement : la corbeille est exclue par défaut,
        # ?trashed=1 ne montre qu'elle. Les actions détail (restore, delete
        # définitif…) doivent voir les tâches à la corbeille.
        if self.action == "list":
            if params.get("trashed") in ("1", "true"):
                Task.purge_expired_trash(self.request.user)
                qs = qs.trashed()
            else:
                qs = qs.active()
        # ?smart=1 : vue agrégée (Aujourd'hui, etc.) → exclut les listes
        # masquées et archivées (module 25.2).
        if params.get("smart") in ("1", "true"):
            qs = qs.visible_in_smart_lists().filter(project__archived=False)
        q = params.get("q")
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(check_items__title__icontains=q)
            ).distinct()
        return qs

    # ----- Transitions -----

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.set_status(Task.Status.COMPLETED)
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"], url_path="wont-do")
    def wont_do(self, request, pk=None):
        task = self.get_object()
        task.set_status(Task.Status.WONT_DO)
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        task = self.get_object()
        task.set_status(Task.Status.NORMAL)
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        task = self.get_object()
        task.restore()
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        task = self.get_object()
        copy = task.duplicate(
            include_children=request.data.get("include_children", True)
        )
        return Response(self.get_serializer(copy).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Premier delete → corbeille ; delete d'une tâche déjà à la corbeille
        (ou ?permanent=1) → suppression définitive."""
        task = self.get_object()
        if task.trashed_at is None and request.query_params.get("permanent") != "1":
            task.trash()
            return Response(status=status.HTTP_204_NO_CONTENT)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="batch")
    def batch_create(self, request):
        """Crée une tâche par ligne (batch paste, module 24.1)."""
        project_id = request.data.get("project")
        lines = request.data.get("lines", [])
        if not project_id or not lines:
            return Response({"detail": "project et lines requis."}, status=status.HTTP_400_BAD_REQUEST)
        from apps.projects.models import Project
        try:
            project = Project.objects.get(pk=project_id, user=request.user)
        except Project.DoesNotExist:
            return Response({"detail": "Liste introuvable."}, status=status.HTTP_400_BAD_REQUEST)
        tasks = [
            Task.objects.create(user=request.user, project=project, title=line.strip())
            for line in lines if line.strip()
        ]
        return Response(self.get_serializer(tasks, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="empty-trash")
    def empty_trash(self, request):
        Task.objects.filter(user=request.user).trashed().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def activity(self, request, pk=None):
        logs = self.get_object().activity.all()[:100]
        return Response(ActivityLogSerializer(logs, many=True).data)


class CheckItemViewSet(viewsets.ModelViewSet):
    queryset = CheckItem.objects.all()
    serializer_class = CheckItemSerializer
    filterset_fields = ["task"]

    def get_queryset(self):
        return self.queryset.filter(task__user=self.request.user)

    def perform_update(self, serializer):
        was_done = serializer.instance.is_done
        item = serializer.save()
        if item.is_done and not was_done:
            item.completed_at = timezone.now()
            item.save()
        elif not item.is_done and was_done:
            item.completed_at = None
            item.save()


class TemplateViewSet(viewsets.ModelViewSet):
    serializer_class = TemplateSerializer
    queryset = Template.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReminderViewSet(viewsets.ModelViewSet):
    queryset = Reminder.objects.all()
    serializer_class = ReminderSerializer
    filterset_fields = ["task"]

    def get_queryset(self):
        return self.queryset.filter(task__user=self.request.user)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    filterset_fields = ["task"]

    def get_queryset(self):
        return self.queryset.filter(task__user=self.request.user)

    def perform_update(self, serializer):
        # Conserve le timestamp d'origine, marque (edited) — module 33.
        serializer.save(edited_at=timezone.now())
