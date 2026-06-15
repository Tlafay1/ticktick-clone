import csv
import io
import json

import django_filters
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.projects.views import OwnedModelViewSet

from .ticktick_import import import_ticktick_csv, looks_like_ticktick_csv
from .models import (
    Attachment, CheckItem, Comment, Reminder, SearchHistory,
    Task, TaskVersion, Template,
)
from .serializers import (
    ActivityLogSerializer,
    AttachmentSerializer,
    CheckItemSerializer,
    CommentSerializer,
    ReminderSerializer,
    SearchHistorySerializer,
    TaskSerializer,
    TaskVersionSerializer,
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
    # Filtres sur la date planifiée (start_date si défini, sinon due_date en fallback)
    scheduled_before = django_filters.IsoDateTimeFilter(method="filter_scheduled_before")
    scheduled_after = django_filters.IsoDateTimeFilter(method="filter_scheduled_after")

    def filter_scheduled_before(self, qs, name, value):
        return qs.filter(
            Q(start_date__lt=value) | Q(start_date__isnull=True, due_date__lt=value)
        )

    def filter_scheduled_after(self, qs, name, value):
        return qs.filter(
            Q(start_date__gte=value) | Q(start_date__isnull=True, due_date__gte=value)
        )

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
            elif params.get("archived") in ("1", "true"):
                qs = qs.filter(archived_at__isnull=False)
            else:
                qs = qs.active().filter(archived_at__isnull=True)
        # ?smart=1 : vue agrégée (Aujourd'hui, etc.) → exclut les listes
        # masquées et archivées (module 25.2).
        if params.get("smart") in ("1", "true"):
            qs = qs.visible_in_smart_lists().filter(project__archived=False)
        q = params.get("q", "").strip()
        # "*" et les chaînes génériques sont traités comme « pas de filtre texte ».
        if q and q not in ("*", "%", ".*", "**"):
            SearchHistory.objects.create(user=self.request.user, query=q)
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(check_items__title__icontains=q)
            ).distinct()
        # ?has_attachments=true : filtre tâches avec PJ
        if params.get("has_attachments") in ("1", "true"):
            qs = qs.filter(attachments__isnull=False).distinct()
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

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        task = self.get_object()
        task.archived_at = timezone.now()
        task.save()
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"], url_path="unarchive")
    def unarchive(self, request, pk=None):
        task = self.get_object()
        task.archived_at = None
        task.save()
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["get"])
    def activity(self, request, pk=None):
        logs = self.get_object().activity.all()[:100]
        return Response(ActivityLogSerializer(logs, many=True).data)

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        task = self.get_object()
        return Response(TaskVersionSerializer(task.versions.all(), many=True).data)

    @action(detail=True, methods=["post"], url_path="restore-version")
    def restore_version(self, request, pk=None):
        task = self.get_object()
        version_id = request.data.get("version_id")
        try:
            version = task.versions.get(pk=version_id)
        except TaskVersion.DoesNotExist:
            return Response({"detail": "Version introuvable."}, status=status.HTTP_404_NOT_FOUND)
        task.description = version.description
        task.save()
        return Response(self.get_serializer(task).data)

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        fmt = request.query_params.get("export_format", "json")
        tasks = self.get_queryset().prefetch_related("tags")
        if fmt == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["id", "title", "description", "status", "priority",
                             "due_date", "project", "tags"])
            for t in tasks:
                writer.writerow([
                    t.id, t.title, t.description, t.status, t.priority,
                    t.due_date.isoformat() if t.due_date else "",
                    t.project.name if t.project else "",
                    ",".join(tag.name for tag in t.tags.all()),
                ])
            return HttpResponse(output.getvalue(), content_type="text/csv",
                                headers={"Content-Disposition": 'attachment; filename="tasks.csv"'})
        data = TaskSerializer(tasks, many=True, context={"request": request}).data
        return HttpResponse(json.dumps(data, default=str), content_type="application/json",
                            headers={"Content-Disposition": 'attachment; filename="tasks.json"'})

    @action(detail=False, methods=["post"], url_path="import")
    def import_tasks(self, request):
        """Import CSV ou JSON de tâches."""
        file = request.FILES.get("file")
        json_data = request.data.get("tasks")

        if json_data:
            items = json_data if isinstance(json_data, list) else json.loads(json_data)
            created = []
            for item in items:
                from apps.projects.models import Project
                project_name = item.get("project", "Inbox")
                project = Project.objects.filter(user=request.user, name=project_name).first()
                if not project:
                    project = Project.objects.filter(user=request.user, is_inbox=True).first()
                t = Task.objects.create(
                    user=request.user,
                    project=project,
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    priority=item.get("priority", 0),
                    status=item.get("status", 0),
                )
                created.append(t)
            return Response({"imported": len(created)}, status=status.HTTP_201_CREATED)

        if file:
            content = file.read().decode("utf-8")
            # Format TickTick officiel (dossiers/listes/tags/dates/sous-tâches/kanban).
            if looks_like_ticktick_csv(content):
                dedupe = request.query_params.get("dedupe") == "1"
                stats = import_ticktick_csv(request.user, content, dedupe=dedupe)
                return Response(stats, status=status.HTTP_201_CREATED)
            # Fallback CSV générique (titre/description/priorité → Inbox).
            reader = csv.DictReader(io.StringIO(content))
            from apps.projects.models import Project
            inbox_project = Project.objects.filter(user=request.user, is_inbox=True).first()
            created = 0
            for row in reader:
                Task.objects.create(
                    user=request.user,
                    project=inbox_project,
                    title=row.get("title", row.get("Task Name", "")),
                    description=row.get("description", row.get("Description", "")),
                    priority=int(row.get("priority", 0) or 0),
                )
                created += 1
            return Response({"imported": created}, status=status.HTTP_201_CREATED)

        return Response({"detail": "Fournir un fichier ou des données JSON."}, status=status.HTTP_400_BAD_REQUEST)


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


class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    parser_classes = [MultiPartParser]
    filterset_fields = ["task"]

    def get_queryset(self):
        return self.queryset.filter(task__user=self.request.user)

    def perform_create(self, serializer):
        f = self.request.FILES.get("file")
        attachment_type = "file"
        if f:
            ct = f.content_type or ""
            if ct.startswith("image/"):
                attachment_type = "image"
            elif ct.startswith("audio/"):
                attachment_type = "audio"
        serializer.save(
            filename=f.name if f else "",
            content_type=f.content_type if f else "",
            size=f.size if f else 0,
            attachment_type=attachment_type,
        )

    def update(self, request, *args, **kwargs):
        """Remplace le fichier (annotation image aplatie — module 32)."""
        instance = self.get_object()
        f = request.FILES.get("file")
        if f:
            instance.file = f
            instance.filename = f.name
            instance.content_type = f.content_type
            instance.size = f.size
            instance.save()
        return Response(AttachmentSerializer(instance).data)


class SearchHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SearchHistorySerializer

    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user)[:20]

    @action(detail=False, methods=["delete"], url_path="clear")
    def clear(self, request):
        SearchHistory.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    filterset_fields = ["task"]

    def get_queryset(self):
        return self.queryset.filter(task__user=self.request.user)

    def perform_update(self, serializer):
        # Conserve le timestamp d'origine, marque (edited) — module 33.
        serializer.save(edited_at=timezone.now())
