from django.conf import settings
from django.db import models


class CalendarSubscription(models.Model):
    """Abonnement ICS en lecture seule (module 4.3)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="calendar_subscriptions",
    )
    name = models.CharField(max_length=120)
    url = models.URLField(max_length=512)
    color = models.CharField(max_length=16, blank=True)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
