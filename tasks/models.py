from django.db import models
from accounts.models import User

class TaskList(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey('ProjectGroup', on_delete=models.SET_NULL, null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    color = models.CharField(max_length=7, null=True, blank=True)  # Hex color code
    icon = models.CharField(max_length=100, null=True, blank=True)
    view_mode = models.CharField(max_length=20, default='list')  # list, kanban, timeline
    is_archived = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class Task(models.Model):
    title = models.TextField()
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    list = models.ForeignKey(TaskList, on_delete=models.CASCADE)
    priority = models.IntegerField(default=0)  # 0=none, 1=low, 3=medium, 5=high
    due_date = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    pinned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
