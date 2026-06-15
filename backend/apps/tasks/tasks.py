"""Tâches Celery : déclenchement des rappels et entretien de la corbeille."""

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.accounts.push import notify_user

from .models import TRASH_RETENTION_DAYS, Reminder, Task


@shared_task
def dispatch_due_reminders():
    """Envoie les rappels arrivés à échéance et non encore dispatchés.

    Idempotent grâce à `Reminder.dispatched_at`. Ignore les rappels de tâches
    terminées, abandonnées ou en corbeille.
    """
    now = timezone.now()
    pending = Reminder.objects.filter(dispatched_at__isnull=True).select_related("task")
    sent = 0
    for reminder in pending:
        task = reminder.task
        if task.status != Task.Status.NORMAL or task.trashed_at is not None:
            continue
        due = reminder.due_at()
        if due is None or due > now:
            continue
        notify_user(
            task.user,
            title=task.title,
            body="Rappel : cette tâche arrive à échéance.",
            url=f"/task/{task.id}",
        )
        reminder.dispatched_at = now
        reminder.save(update_fields=["dispatched_at"])
        sent += 1
    return sent


@shared_task
def purge_expired_trash():
    """Supprime définitivement les tâches en corbeille depuis > 30 jours (tous users)."""
    limit = timezone.now() - timedelta(days=TRASH_RETENTION_DAYS)
    deleted, _ = Task.objects.filter(trashed_at__lt=limit).delete()
    return deleted
