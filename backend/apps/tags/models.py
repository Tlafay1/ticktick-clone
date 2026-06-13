from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Tag(models.Model):
    """Tag hiérarchique (module 3). Le renommage se propage naturellement
    aux enfants via `parent`."""
    
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name

    def merge_into(self, target):
        """Fusionne ce tag avec un autre (déplace les enfants et les tâches)."""
        # Move children to target
        for child in Tag.objects.filter(parent=self):
            child.parent = target
            child.save()
        
        # Move tasks that had this tag or any of its descendants to the target tag
        from apps.tasks.models import Task
        
        # Get all descendant tags including self
        descendant_tags = []
        queue = [self]
        
        while queue:
            current = queue.pop(0)
            descendant_tags.append(current)
            children = Tag.objects.filter(parent=current)
            queue.extend(children)
        
        descendant_ids = [tag.id for tag in descendant_tags]
        
        # Move tasks that had any of the descendant tags to target
        for task in Task.objects.filter(tags__in=descendant_ids):
            task.tags.remove(*Tag.objects.filter(id__in=descendant_ids))
            task.tags.add(target)
        
        # Delete this tag
        self.delete()
