from django.conf import settings
from django.db import models


class Tag(models.Model):
    """Tag hiérarchique (module 3). Le renommage se propage naturellement
    puisque les tâches référencent l'id, pas le nom."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tags"
    )
    name = models.CharField(max_length=120)
    color = models.CharField(max_length=16, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="children",
    )
    sort_order = models.BigIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_tag_name")
        ]

    def __str__(self):
        return self.name

    def merge_into(self, target):
        """Fusion de tags (module 3.1) : re-tague toutes les tâches puis supprime."""
        for task in self.tasks.all():
            task.tags.add(target)
        self.children.update(parent=target)
        self.delete()
