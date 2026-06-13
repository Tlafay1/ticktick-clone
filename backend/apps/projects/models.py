from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ProjectGroup(models.Model):
    """Dossier de listes (module 2.1)."""
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    collapsed = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    """Une « liste » TickTick."""
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(ProjectGroup, null=True, blank=True, on_delete=models.SET_NULL)
    color = models.CharField(max_length=7, null=True, blank=True)  # Hex color code
    icon = models.CharField(max_length=50, null=True, blank=True)  # Emoji or preset name
    view_mode = models.CharField(
        max_length=10,
        choices=[
            ("list", "List"),
            ("kanban", "Kanban"),
            ("timeline", "Timeline"),
        ],
        default="list"
    )
    archived = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    
    # Smart list fields
    is_smart = models.BooleanField(default=False)
    filter_rules = models.JSONField(default=list, blank=True)  # Filter rules for smart lists
    grouping = models.CharField(max_length=50, null=True, blank=True)  # Grouping field
    sorting = models.CharField(max_length=50, null=True, blank=True)  # Sorting field
    
    # Hidden from smart lists (for exclusion)
    hidden_from_smart_lists = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Section(models.Model):
    """Colonne Kanban / section d'une liste (module 5.1)."""
    name = models.CharField(max_length=255)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    sort_order = models.PositiveIntegerField(default=0)
    collapsed = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name
