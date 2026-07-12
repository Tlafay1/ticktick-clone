"""Tâches Celery : rappels d'habitudes (indépendants des rappels de tâches)."""

from celery import shared_task
from django.utils import timezone

from apps.accounts.fcm import send_fcm
from apps.accounts.push import notify_user

from .models import Habit, HabitReminder


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

    Idempotent via `HabitReminder.last_sent_on`. Saute les habitudes archivées,
    non dues aujourd'hui (jours précis / intervalle) ou déjà complétées.
    """
    now = timezone.localtime()
    today = now.date()
    pending = (
        HabitReminder.objects.filter(time__lte=now.time(), habit__archived=False)
        .exclude(last_sent_on=today)
        .select_related("habit", "habit__user")
    )
    sent = 0
    for reminder in pending:
        habit = reminder.habit
        skip = (
            not _due_today(habit, today)
            or habit.checkins.filter(date=today, completed=True).exists()
        )
        if not skip:
            for _push in (notify_user, send_fcm):
                _push(
                    habit.user,
                    title=habit.name,
                    body=habit.motto or "C'est l'heure de votre habitude !",
                    url="/habits",
                )
            sent += 1
        # Dans tous les cas, ne pas retenter avant demain.
        reminder.last_sent_on = today
        reminder.save(update_fields=["last_sent_on"])
    return sent
