from django.db import models
from accounts.models import User

class ProjectGroup(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    collapsed = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name

class Project(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(ProjectGroup, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.name
