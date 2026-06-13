from django.conf import settings
from django.db import models


class Tag(models.Model):
    """Tag hiérarchique (module 3). Le renommage se propage naturellement
    aux enfants via `parent`."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tags"
    )
    name = models.CharField(max_length=120)
    color = models.CharField(max_length=16, blank=True)
    sort_order = models.BigIntegerField(default=0)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=("user", "name"), name="unique_tag_name")
        ]

    def __str__(self):
        return self.name

    def merge_into(self, target):
        """Fusionne ce tag dans target : déplace enfants + tâches, puis supprime."""
        Tag.objects.filter(parent=self).update(parent=target)

        from apps.tasks.models import Task
        for task in Task.objects.filter(tags=self):
            task.tags.remove(self)
            task.tags.add(target)

        self.delete()
