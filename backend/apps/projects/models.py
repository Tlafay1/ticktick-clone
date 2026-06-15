from django.conf import settings
from django.db import models


class ProjectGroup(models.Model):
    """Dossier de listes (module 2.1)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_groups"
    )
    name = models.CharField(max_length=120)
    sort_order = models.BigIntegerField(default=0)
    collapsed = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class Project(models.Model):
    """Une « liste » TickTick."""

    class ViewMode(models.TextChoices):
        LIST = "list"
        KANBAN = "kanban"
        TIMELINE = "timeline"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects"
    )
    group = models.ForeignKey(
        ProjectGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="projects"
    )
    name = models.CharField(max_length=120)
    color = models.CharField(max_length=16, blank=True)
    icon = models.CharField(max_length=64, blank=True)
    view_mode = models.CharField(
        max_length=16, choices=ViewMode, default=ViewMode.LIST
    )
    sort_order = models.BigIntegerField(default=0)
    is_inbox = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    hidden_from_smart_lists = models.BooleanField(default=False)
    # Smart list fields (module 2.3)
    is_smart = models.BooleanField(default=False)
    filter_rules = models.JSONField(default=list, blank=True)
    grouping = models.CharField(max_length=50, null=True, blank=True)
    sorting = models.CharField(max_length=50, null=True, blank=True)
    bg_color = models.CharField(max_length=32, blank=True)
    bg_image_url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=("user",), condition=models.Q(is_inbox=True), name="unique_inbox_per_user"
            )
        ]

    def __str__(self):
        return self.name


class Section(models.Model):
    """Colonne Kanban / section d'une liste (module 5.1)."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=120)
    sort_order = models.BigIntegerField(default=0)
    collapsed = models.BooleanField(default=False)
    is_done = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name
