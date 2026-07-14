import secrets

from django.conf import settings
from django.db import models


def _generate_secret():
    return secrets.token_urlsafe(32)


class Webhook(models.Model):
    """Abonnement webhook sortant (intégration n8n / IA / scripts).

    `events` vide = tous les événements. Chaque livraison est signée HMAC-SHA256
    du corps avec `secret` (en-tête `X-Webhook-Signature: sha256=…`).
    """

    EVENTS = [
        "task.created",
        "task.updated",
        "task.completed",
        "task.deleted",
        "task.claimed",
        "project.created",
        "project.updated",
        "project.deleted",
        "habit.checkin",
        "pomodoro.started",
        "pomodoro.stopped",
        "pomodoro.completed",
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="webhooks"
    )
    url = models.URLField(max_length=500)
    events = models.JSONField(default=list, blank=True)
    secret = models.CharField(max_length=64, default=_generate_secret)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.url} ({', '.join(self.events) or 'tous'})"

    def matches(self, event):
        return not self.events or event in self.events


class WebhookDelivery(models.Model):
    """Journal d'une tentative de livraison (debug / observabilité n8n)."""

    webhook = models.ForeignKey(
        Webhook, on_delete=models.CASCADE, related_name="deliveries"
    )
    event = models.CharField(max_length=64)
    # Id d'événement stable (idempotence côté consommateur, constant à travers les retries).
    event_id = models.CharField(max_length=36, blank=True, db_index=True)
    payload = models.JSONField(default=dict)
    status_code = models.IntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
