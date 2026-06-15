from datetime import date

from django.conf import settings
from django.db import models


class Countdown(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="countdowns")
    title = models.CharField(max_length=120)
    target_date = models.DateField()
    description = models.TextField(blank=True)  # riche (markdown)
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-pinned", "target_date"]

    def days_remaining(self):
        delta = self.target_date - date.today()
        return delta.days

    def __str__(self):
        return self.title
