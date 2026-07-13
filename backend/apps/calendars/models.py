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


class CalendarEvent(models.Model):
    """Événement importé (lecture seule) d'un abonnement ICS.

    Les récurrences sont dépliées à l'import (fenêtre glissante) : une ligne
    par occurrence, identifiée par (subscription, uid, start).
    """

    subscription = models.ForeignKey(
        CalendarSubscription, on_delete=models.CASCADE, related_name="events"
    )
    uid = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)

    class Meta:
        ordering = ["start"]
        constraints = [
            models.UniqueConstraint(
                fields=("subscription", "uid", "start"), name="unique_event_occurrence"
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.start:%Y-%m-%d})"
