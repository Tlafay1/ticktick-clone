"""Tâches Celery : rappels d'habitudes (indépendants des rappels de tâches)."""

import logging

from celery import shared_task
from django.utils import timezone

from apps.accounts.fcm import send_fcm
from apps.accounts.models import UserSettings
from apps.accounts.push import notify_user

from .models import Habit, HabitReminder

logger = logging.getLogger(__name__)


def _due_today(habit, today):
    """L'habitude est-elle attendue aujourd'hui selon sa fréquence ?"""
    if habit.frequency == Habit.Frequency.SPECIFIC_DAYS:
        days = habit.freq_config.get("days", [])
        return today.weekday() in days
    if habit.frequency == Habit.Frequency.INTERVAL:
        every = int(habit.freq_config.get("every", 1) or 1)
        last = (
            habit.checkins.filter(completed=True)
            .order_by("-date")
            .values_list("date", flat=True)
            .first()
        )
        return last is None or (today - last).days >= every
    # daily / weekly / weekly_goal : rappel quotidien
    return True


@shared_task
def dispatch_habit_reminders():
    """Envoie les rappels d'habitude dont l'heure est passée (1×/jour chacun).

    L'heure d'un rappel est « murale » : elle s'interprète dans le fuseau de
    l'utilisateur. Idempotent via `HabitReminder.last_sent_on`. Saute les
    habitudes archivées, non dues aujourd'hui ou déjà complétées. Les appareils
    Android récents les programment en local (FCM les saute).
    """
    pending = HabitReminder.objects.filter(habit__archived=False).select_related(
        "habit", "habit__user"
    )
    sent = 0
    for reminder in pending:
        habit = reminder.habit
        user_settings, _ = UserSettings.objects.get_or_create(user=habit.user)
        now = timezone.now().astimezone(user_settings.tzinfo)
        today = now.date()
        if reminder.last_sent_on == today or reminder.time > now.time():
            continue
        skip = (
            not _due_today(habit, today)
            or habit.checkins.filter(date=today, completed=True).exists()
        )
        if not skip:
            payload = {
                "title": habit.name,
                "body": habit.motto or "C'est l'heure de votre habitude !",
                "url": "/habits",
            }
            for push, extra in (
                (notify_user, {"tag": f"habit-{reminder.id}-{today.isoformat()}"}),
                (send_fcm, {"reminder": True}),
            ):
                try:
                    push(habit.user, **payload, **extra)
                except Exception:
                    logger.exception("Échec d'envoi du rappel d'habitude %s", reminder.id)
            sent += 1
        # Dans tous les cas, ne pas retenter avant demain.
        reminder.last_sent_on = today
        reminder.save(update_fields=["last_sent_on"])
    return sent
