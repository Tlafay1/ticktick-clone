from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

TRASH_RETENTION_DAYS = 30
MAX_SUBTASK_DEPTH = 5  # profondeur max d'imbrication des sous-tâches (Tier 1)


class TaskQuerySet(models.QuerySet):
    def active(self):
        return self.filter(trashed_at__isnull=True)

    def trashed(self):
        return self.filter(trashed_at__isnull=False)

    def visible_in_smart_lists(self):
        """Exclut les tâches des listes masquées (module 25.2)."""
        return self.filter(project__hidden_from_smart_lists=False)


class Task(models.Model):
    class Status(models.IntegerChoices):
        # Valeurs alignées sur TickTick : 0 normal, 2 terminé, -1 abandonné.
        NORMAL = 0
        COMPLETED = 2
        WONT_DO = -1

    class Priority(models.IntegerChoices):
        # Valeurs TickTick : 0/1/3/5.
        NONE = 0
        LOW = 1
        MEDIUM = 3
        HIGH = 5

    class RepeatFrom(models.TextChoices):
        DUE_DATE = "due"
        COMPLETION = "completion"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks"
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="tasks"
    )
    section = models.ForeignKey(
        "projects.Section", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="tasks",
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE,
        related_name="children",
    )

    title = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    status = models.SmallIntegerField(choices=Status, default=Status.NORMAL)
    priority = models.PositiveSmallIntegerField(choices=Priority, default=Priority.NONE)
    progress = models.PositiveSmallIntegerField(default=0)  # 0–100, pas de 10
    is_pinned = models.BooleanField(default=False)
    pinned_at = models.DateTimeField(null=True, blank=True)

    # Dates : TickTick stocke start/due + flag all_day + fuseau propre à la tâche.
    start_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=True)
    timezone_name = models.CharField(max_length=64, blank=True)
    # planned_date : date à laquelle l'utilisateur prévoit de travailler sur la tâche
    planned_date = models.DateTimeField(null=True, blank=True)
    # end_date : date de fin effective du travail (distincte de due_date)
    end_date = models.DateTimeField(null=True, blank=True)

    # Récurrence (RFC 5545) — moteur complet au jalon 2.
    rrule = models.CharField(max_length=512, blank=True)
    repeat_from = models.CharField(
        max_length=16, choices=RepeatFrom, default=RepeatFrom.DUE_DATE
    )

    tags = models.ManyToManyField("tags.Tag", blank=True, related_name="tasks")

    sort_order = models.BigIntegerField(default=0)
    external_id = models.CharField(max_length=64, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    trashed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    estimated_pomos = models.PositiveSmallIntegerField(default=0)  # estimation Pomodoro (M21.2)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["user", "due_date"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return self.title

    # ----- Hiérarchie -----

    @property
    def depth(self):
        # Défense en profondeur : borné par un ensemble de visités pour ne
        # jamais boucler si un cycle parent existe malgré la validation.
        depth, node, seen = 0, self, {self.pk}
        while node.parent_id is not None and node.parent_id not in seen:
            seen.add(node.parent_id)
            depth += 1
            node = node.parent
        return depth

    def descendants(self):
        """Tous les descendants (l'imbrication étant ≤ 5, on itère par niveau)."""
        # Même défense : un id déjà visité n'est jamais réexploré (cycle).
        result, frontier, seen = [], [self.id], {self.id}
        while frontier:
            level = [t for t in Task.objects.filter(parent_id__in=frontier)
                     if t.id not in seen]
            result.extend(level)
            seen.update(t.id for t in level)
            frontier = [t.id for t in level]
        return result

    # ----- Transitions d'état -----

    def _next_recurrence(self, from_dt):
        """Calcule la prochaine occurrence de l'RRULE après `from_dt`."""
        from dateutil.rrule import rrulestr
        try:
            rule = rrulestr(self.rrule, dtstart=from_dt, ignoretz=True)
            after = rule.after(from_dt, inc=False)
            return after
        except Exception:
            return None

    def set_status(self, status):
        now = timezone.now()
        self.status = status
        self.completed_at = now if status != Task.Status.NORMAL else None
        if status == Task.Status.COMPLETED:
            self.progress = 100
            if self.rrule:
                base = now if self.repeat_from == Task.RepeatFrom.COMPLETION else self.due_date
                if base:
                    next_dt = self._next_recurrence(base.replace(tzinfo=None))
                    if next_dt:
                        from datetime import timezone as dt_timezone
                        delta = (self.due_date - self.start_date) if self.start_date and self.due_date else None
                        self.due_date = next_dt.replace(tzinfo=dt_timezone.utc)
                        if delta is not None:
                            self.start_date = self.due_date - delta
                        self.status = Task.Status.NORMAL
                        self.completed_at = None
                        self.progress = 0
        self.save()
        if status != Task.Status.NORMAL:
            # Terminer/abandonner un parent emporte ses sous-tâches actives.
            for child in self.descendants():
                if child.status == Task.Status.NORMAL and child.trashed_at is None:
                    child.status = status
                    child.completed_at = now
                    child.save()
            self._maybe_complete_parent()
        ActivityLog.log(self, "status_changed", status=status)

    def _maybe_complete_parent(self):
        """Cocher la dernière sous-tâche restante termine le parent (Tier 1)."""
        parent = self.parent
        if parent is None or parent.status != Task.Status.NORMAL:
            return
        siblings = parent.children.filter(trashed_at__isnull=True)
        if siblings.exists() and not siblings.filter(status=Task.Status.NORMAL).exists():
            parent.set_status(Task.Status.COMPLETED)

    def trash(self):
        now = timezone.now()
        self.trashed_at = now
        self.save()
        for child in self.descendants():
            if child.trashed_at is None:
                child.trashed_at = now
                child.save()
        ActivityLog.log(self, "trashed")

    def restore(self):
        marker = self.trashed_at
        self.trashed_at = None
        # Une sous-tâche restaurée seule remonte à la racine si son parent
        # est encore à la corbeille.
        if self.parent and self.parent.trashed_at is not None:
            self.parent = None
        self.save()
        # Restaure les descendants supprimés au même moment.
        if marker:
            for child in self.descendants():
                if child.trashed_at == marker:
                    child.trashed_at = None
                    child.save()
        ActivityLog.log(self, "restored")

    @classmethod
    def purge_expired_trash(cls, user):
        limit = timezone.now() - timedelta(days=TRASH_RETENTION_DAYS)
        cls.objects.filter(user=user, trashed_at__lt=limit).delete()

    # ----- Duplication (module 1.2) -----

    def duplicate(self, include_children=True, parent=None, title_suffix=" (copy)"):
        copy = Task.objects.create(
            user=self.user,
            project=self.project,
            section=self.section,
            parent=parent if parent is not None else self.parent,
            title=self.title + (title_suffix if parent is None else ""),
            description=self.description,
            priority=self.priority,
            progress=self.progress,
            start_date=self.start_date,
            due_date=self.due_date,
            is_all_day=self.is_all_day,
            timezone_name=self.timezone_name,
            rrule=self.rrule,
            repeat_from=self.repeat_from,
            sort_order=self.sort_order + 1,
        )
        copy.tags.set(self.tags.all())
        for item in self.check_items.all():
            CheckItem.objects.create(
                task=copy, title=item.title, sort_order=item.sort_order
            )
        if include_children:
            for child in self.children.filter(trashed_at__isnull=True):
                child.duplicate(include_children=True, parent=copy, title_suffix="")
        return copy


class Reminder(models.Model):
    """Rappel associé à une tâche — jusqu'à 5 par tâche (module 1.1 / M15)."""

    class TriggerType(models.TextChoices):
        RELATIVE = "relative"  # X minutes avant l'échéance
        ABSOLUTE = "absolute"  # date+heure fixe

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="reminders")
    trigger_type = models.CharField(max_length=16, choices=TriggerType, default=TriggerType.RELATIVE)
    minutes_before = models.IntegerField(null=True, blank=True)  # pour trigger_type=relative
    trigger_at = models.DateTimeField(null=True, blank=True)    # pour trigger_type=absolute
    annoying = models.BooleanField(default=False)               # M15 : alerte persistante
    dispatched_at = models.DateTimeField(null=True, blank=True)  # horodatage d'envoi (idempotence)

    class Meta:
        ordering = ["id"]

    def due_at(self):
        """Instant où le rappel doit se déclencher, ou None si indéterminable."""
        if self.trigger_type == self.TriggerType.ABSOLUTE:
            return self.trigger_at
        if self.minutes_before is not None and self.task.due_date:
            return self.task.due_date - timedelta(minutes=self.minutes_before)
        return None

    def __str__(self):
        return f"Reminder<task={self.task_id} {self.trigger_type}>"


class CheckItem(models.Model):
    """Tier 2 : item de checklist interne à une tâche (module 31)."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="check_items")
    title = models.CharField(max_length=512)
    is_done = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.BigIntegerField(default=0)

    class Meta:
        ordering = ["is_done", "sort_order", "id"]  # les items cochés vont en bas

    def __str__(self):
        return self.title


class Comment(models.Model):
    """Journal personnel horodaté d'une tâche (module 33)."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]


class Template(models.Model):
    """Template de tâche ou de liste (module 23)."""

    class Scope(models.TextChoices):
        TASK = "task"
        PROJECT = "project"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="templates"
    )
    scope = models.CharField(max_length=16, choices=Scope, default=Scope.TASK)
    name = models.CharField(max_length=256)
    data = models.JSONField(default=dict)  # snapshot sérialisé de la tâche ou liste

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Attachment(models.Model):
    """Pièce jointe à une tâche (module 1.1 / J5)."""

    class AttachmentType(models.TextChoices):
        FILE = "file"
        IMAGE = "image"
        AUDIO = "audio"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="attachments/")
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=128, blank=True)
    size = models.PositiveIntegerField(default=0)
    attachment_type = models.CharField(max_length=16, choices=AttachmentType, default=AttachmentType.FILE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class TaskVersion(models.Model):
    """Historique de versions de la description d'une tâche (module 27.1)."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="versions")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class SearchHistory(models.Model):
    """Historique des recherches récentes (module 10.2)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_history"
    )
    query = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ActivityLog(models.Model):
    """Historique des modifications d'une tâche (module 1.1)."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="activity")
    action = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def log(cls, task, action, **payload):
        return cls.objects.create(task=task, action=action, payload=payload)
