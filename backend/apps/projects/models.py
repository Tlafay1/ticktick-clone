from django.conf import settings
from django.db import models

# Pas d'ordre fractionnaire : on espace les sort_order de ce pas, le client
# insère entre deux valeurs et le serveur renumérote si l'écart s'épuise.
SORT_STEP = 65536


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
        ProjectGroup, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="projects",
    )
    name = models.CharField(max_length=120)
    color = models.CharField(max_length=16, blank=True)  # hex ou vide
    icon = models.CharField(max_length=64, blank=True)  # emoji ou nom d'icône preset
    view_mode = models.CharField(max_length=16, choices=ViewMode, default=ViewMode.LIST)
    sort_order = models.BigIntegerField(default=0)
    is_inbox = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    # « Do Not Show in Smart Lists » (module 25.2)
    hidden_from_smart_lists = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_inbox=True),
                name="unique_inbox_per_user",
            )
        ]

    def __str__(self):
        return self.name


class Section(models.Model):
    """Colonne Kanban / section d'une liste (module 5.1)."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="sections"
    )
    name = models.CharField(max_length=120)
    sort_order = models.BigIntegerField(default=0)
    collapsed = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.project.name} / {self.name}"
