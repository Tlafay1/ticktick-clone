import csv
import datetime
import io
import json
from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import django_filters
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.accounts.actors import get_actor
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


def _resolve_tz(name):
    """ZoneInfo demandé (`?tz=`), UTC si absent ou invalide."""
    if not name:
        return datetime.timezone.utc
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return datetime.timezone.utc


def _day_end_utc(local_date, tz):
    """Instant UTC correspondant à la fin (minuit du lendemain) d'un jour local."""
    start = datetime.datetime.combine(local_date, datetime.time.min, tzinfo=tz)
    return (start + timedelta(days=1)).astimezone(datetime.timezone.utc)


def _diff(before, after):
    """Champs modifiés entre deux snapshots sérialisés : {champ: {old, new}}."""
    return {
        key: {"old": before.get(key), "new": after.get(key)}
        for key in after
        if before.get(key) != after.get(key)
    }


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
    # ?project=<id> : liste normale → filtre FK ; smart list custom → ses
    # filter_rules s'appliquent à l'ensemble des tâches (module 2.3).
    project = django_filters.NumberFilter(method="filter_project")

    def filter_project(self, qs, name, value):
        from apps.projects.filters import apply_smart_list
        from apps.projects.models import Project

        project = Project.objects.filter(pk=int(value), user=self.request.user).first()
        if project is not None and project.is_smart:
            return apply_smart_list(qs, project)
        return qs.filter(project_id=int(value))

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
        fields = ["section", "parent", "status", "priority", "is_pinned"]


class TaskViewSet(OwnedModelViewSet):
    queryset = Task.objects.all().prefetch_related("check_items", "tags", "reminders")
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
        # ?overdue=1 : échéance passée ET tâche encore active (en retard).
        if params.get("overdue") in ("1", "true"):
            qs = qs.filter(due_date__lt=timezone.now(), status=Task.Status.NORMAL)
        return qs

    # ----- Webhooks -----

    def _emit(self, event, task, changes=None):
        from apps.webhooks.dispatch import emit

        emit(self.request.user, event, self.get_serializer(task).data,
             actor=get_actor(self.request), changes=changes)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        self._emit("task.created", serializer.instance)

    def perform_update(self, serializer):
        before = self.get_serializer(serializer.instance).data
        was_claimed = bool(serializer.instance.claimed_by)
        serializer.save()
        after = self.get_serializer(serializer.instance).data
        changes = _diff(before, after)
        self._emit("task.updated", serializer.instance, changes=changes)
        # Revendication d'une tâche par un agent : "" → renseigné.
        if not was_claimed and serializer.instance.claimed_by:
            self._emit("task.claimed", serializer.instance)

    # ----- Transitions -----

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.set_status(Task.Status.COMPLETED, actor=get_actor(request))
        self._emit("task.completed", task)
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"], url_path="wont-do")
    def wont_do(self, request, pk=None):
        task = self.get_object()
        task.set_status(Task.Status.WONT_DO, actor=get_actor(request))
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        task = self.get_object()
        task.set_status(Task.Status.NORMAL, actor=get_actor(request))
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        task = self.get_object()
        task.restore(actor=get_actor(request))
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
            task.trash(actor=get_actor(request))
            return Response(status=status.HTTP_204_NO_CONTENT)
        snapshot = self.get_serializer(task).data
        task.delete()
        from apps.webhooks.dispatch import emit

        emit(request.user, "task.deleted", snapshot, actor=get_actor(request))
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

    # ----- Vues agrégées pour agents -----

    def _active(self):
        """Tâches actives, non archivées, hors corbeille (base des vues agrégées)."""
        return self.get_queryset().active().filter(archived_at__isnull=True)

    @extend_schema(
        parameters=[OpenApiParameter("tz", str, description="Fuseau (ex. Europe/Paris) ; défaut UTC.")],
        responses=OpenApiTypes.OBJECT,
        description="Tâches dues aujourd'hui + en retard, en un appel.",
    )
    @action(detail=False, methods=["get"], url_path="today")
    def today(self, request):
        """Tâches dues aujourd'hui + en retard, en un seul appel (module agents).

        `?tz=` (ex. Europe/Paris) borne la journée dans ce fuseau ; défaut UTC.
        """
        tz = _resolve_tz(request.query_params.get("tz"))
        now = timezone.now()
        local_today = timezone.localtime(now, tz).date()
        end_of_day = _day_end_utc(local_today, tz)
        qs = self._active().filter(due_date__isnull=False, status=Task.Status.NORMAL)
        overdue = qs.filter(due_date__lt=now)
        today = qs.filter(due_date__gte=now, due_date__lt=end_of_day)
        ser = self.get_serializer
        return Response({
            "date": local_today.isoformat(),
            "today": ser(today, many=True).data,
            "overdue": ser(overdue, many=True).data,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter("days", int, description="Nombre de jours (défaut 7, max 90)."),
            OpenApiParameter("tz", str, description="Fuseau pour le regroupement ; défaut UTC."),
        ],
        responses=OpenApiTypes.OBJECT,
        description="Nombre de tâches actives par jour d'échéance sur N jours.",
    )
    @action(detail=False, methods=["get"], url_path="density")
    def density(self, request):
        """Nombre de tâches actives par jour d'échéance sur les N prochains jours.

        `?days=N` (défaut 7, max 90), `?tz=` pour le regroupement par jour.
        Renvoie une ligne par jour, y compris les jours à zéro.
        """
        tz = _resolve_tz(request.query_params.get("tz"))
        try:
            days = int(request.query_params.get("days", 7))
        except ValueError:
            days = 7
        days = max(1, min(days, 90))
        now = timezone.now()
        start_day = timezone.localtime(now, tz).date()
        window_end = _day_end_utc(start_day + timedelta(days=days - 1), tz)
        qs = self._active().filter(
            due_date__isnull=False, status=Task.Status.NORMAL,
            due_date__gte=now, due_date__lt=window_end,
        )
        counts = {}
        for due in qs.values_list("due_date", flat=True):
            key = timezone.localtime(due, tz).date().isoformat()
            counts[key] = counts.get(key, 0) + 1
        result = [
            {"date": (start_day + timedelta(days=i)).isoformat(),
             "count": counts.get((start_day + timedelta(days=i)).isoformat(), 0)}
            for i in range(days)
        ]
        return Response(result)

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses=OpenApiTypes.OBJECT,
        description="Complete/update/reschedule une liste d'ids ; résultat par item.",
    )
    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        """Opère sur une liste d'ids en un appel, résultat par item.

        Body : {"action": "complete"|"update"|"reschedule", "ids": [...],
                "data": {...}}. Jamais tout-ou-rien : chaque item renvoie
        {"id", "ok", "error"?}. `update`/`reschedule` réutilisent le
        TaskSerializer en PATCH partiel.
        """
        bulk_action = request.data.get("action")
        ids = request.data.get("ids", [])
        data = request.data.get("data", {}) or {}
        if bulk_action not in ("complete", "update", "reschedule"):
            return Response(
                {"detail": "action doit être complete, update ou reschedule."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids requis (liste non vide)."},
                            status=status.HTTP_400_BAD_REQUEST)
        if bulk_action == "reschedule":
            data = {k: data.get(k) for k in ("start_date", "due_date") if k in data}
        actor = get_actor(request)
        results = []
        for task_id in ids:
            task = self.get_queryset().filter(pk=task_id).first()
            if task is None:
                results.append({"id": task_id, "ok": False, "error": "introuvable"})
                continue
            try:
                if bulk_action == "complete":
                    task.set_status(Task.Status.COMPLETED, actor=actor)
                    self._emit("task.completed", task)
                else:
                    serializer = self.get_serializer(task, data=data, partial=True)
                    serializer.is_valid(raise_exception=True)
                    before = self.get_serializer(task).data
                    serializer.save()
                    after = self.get_serializer(serializer.instance).data
                    self._emit("task.updated", serializer.instance,
                               changes=_diff(before, after))
                results.append({"id": task_id, "ok": True})
            except Exception as exc:  # erreur par item, on continue
                detail = exc.detail if hasattr(exc, "detail") else str(exc)
                results.append({"id": task_id, "ok": False, "error": detail})
        return Response({"results": results})

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
