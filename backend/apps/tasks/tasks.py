"""Tâches Celery : déclenchement des rappels et entretien de la corbeille."""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.accounts.fcm import send_fcm
from apps.accounts.push import notify_user

from .models import TRASH_RETENTION_DAYS, Reminder, Task

logger = logging.getLogger(__name__)

# Au-delà de ce retard, un rappel n'en est plus un : il est marqué envoyé sans
# notifier (évite une rafale de vieux rappels après une panne du worker).
STALE_AFTER = timedelta(hours=2)


def reminder_tag(reminder, due):
    """Identifiant partagé par tous les canaux : le navigateur remplace au lieu d'empiler."""
    return f"reminder-{reminder.id}-{int(due.timestamp())}"


@shared_task
def dispatch_due_reminders():
    """Envoie les rappels arrivés à échéance (Web Push + FCM).

    Un rappel est dû une fois par échéance : s'il a été envoyé AVANT son instant
    de déclenchement actuel (récurrence avancée, tâche reportée), il est réarmé.
    Les appareils Android récents programment leurs rappels en local : FCM les
    saute (cf. FCMDevice.local_reminders).
    """
    now = timezone.now()
    pending = Reminder.objects.filter(
        task__status=Task.Status.NORMAL, task__trashed_at__isnull=True
    ).select_related("task", "task__user")
    sent = 0
    for reminder in pending:
        due = reminder.due_at()
        if due is None or due > now:
            continue
        if reminder.dispatched_at is not None and reminder.dispatched_at >= due:
            continue
        if now - due <= STALE_AFTER:
            task = reminder.task
            payload = {
                "title": task.title,
                "body": "Rappel : cette tâche arrive à échéance.",
                "url": f"/task/{task.id}",
            }
            for push, extra in (
                (notify_user, {"tag": reminder_tag(reminder, due)}),
                (send_fcm, {"reminder": True}),
            ):
                try:
                    push(task.user, **payload, **extra)
                except Exception:
                    # Un canal en échec ne doit ni bloquer les autres ni faire
                    # renvoyer ce rappel chaque minute (la boucle d'avant).
                    logger.exception("Échec d'envoi du rappel %s", reminder.id)
            sent += 1
        reminder.dispatched_at = now
        reminder.save(update_fields=["dispatched_at"])
    return sent


@shared_task
def purge_expired_trash():
    """Supprime définitivement les tâches en corbeille depuis > 30 jours (tous users)."""
    limit = timezone.now() - timedelta(days=TRASH_RETENTION_DAYS)
    deleted, _ = Task.objects.filter(trashed_at__lt=limit).delete()
    return deleted
