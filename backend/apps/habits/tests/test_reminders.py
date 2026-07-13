"""Dispatch des rappels d'habitudes (module 6 — rappels indépendants des tâches)."""

from datetime import date, time, timedelta

import pytest
from django.utils import timezone

from apps.habits import tasks as habit_tasks
from apps.habits.models import Habit, HabitCheckIn, HabitReminder

pytestmark = pytest.mark.django_db

PAST = time(0, 0)  # toujours <= l'heure courante


@pytest.fixture
def pushes(monkeypatch):
    """Capture les notifications envoyées (web push + FCM neutralisés)."""
    calls = []

    def fake_push(user, title, body, url):
        calls.append({"user": user, "title": title, "body": body, "url": url})

    monkeypatch.setattr(habit_tasks, "notify_user", fake_push)
    monkeypatch.setattr(habit_tasks, "send_fcm", fake_push)
    return calls


def _habit(user, **kwargs):
    return Habit.objects.create(user=user, name="Lire", **kwargs)


def test_due_reminder_sent_once_per_day(user, pushes):
    habit = _habit(user, motto="10 pages par jour")
    reminder = HabitReminder.objects.create(habit=habit, time=PAST)

    assert habit_tasks.dispatch_habit_reminders() == 1
    # web push + FCM
    assert len(pushes) == 2
    assert pushes[0]["title"] == "Lire"
    assert pushes[0]["body"] == "10 pages par jour"
    assert pushes[0]["url"] == "/habits"

    reminder.refresh_from_db()
    assert reminder.last_sent_on == timezone.localdate()

    # Idempotent : un second passage le même jour n'envoie rien.
    assert habit_tasks.dispatch_habit_reminders() == 0
    assert len(pushes) == 2


def test_future_reminder_not_sent(user, pushes):
    habit = _habit(user)
    HabitReminder.objects.create(habit=habit, time=time(23, 59, 59))
    assert habit_tasks.dispatch_habit_reminders() == 0
    assert pushes == []


def test_archived_habit_skipped(user, pushes):
    habit = _habit(user, archived=True)
    HabitReminder.objects.create(habit=habit, time=PAST)
    assert habit_tasks.dispatch_habit_reminders() == 0
    assert pushes == []


def test_already_completed_today_skipped(user, pushes):
    habit = _habit(user)
    HabitCheckIn.objects.create(habit=habit, date=timezone.localdate(), completed=True)
    HabitReminder.objects.create(habit=habit, time=PAST)
    assert habit_tasks.dispatch_habit_reminders() == 0
    assert pushes == []


def test_specific_days_only_on_configured_weekday(user, pushes):
    today_wd = timezone.localdate().weekday()
    off_day = _habit(
        user,
        frequency=Habit.Frequency.SPECIFIC_DAYS,
        freq_config={"days": [(today_wd + 1) % 7]},
    )
    on_day = _habit(
        user,
        frequency=Habit.Frequency.SPECIFIC_DAYS,
        freq_config={"days": [today_wd]},
    )
    HabitReminder.objects.create(habit=off_day, time=PAST)
    HabitReminder.objects.create(habit=on_day, time=PAST)

    assert habit_tasks.dispatch_habit_reminders() == 1
    assert all(c["title"] == on_day.name for c in pushes)


def test_interval_respects_days_since_last_checkin(user, pushes):
    habit = _habit(user, frequency=Habit.Frequency.INTERVAL, freq_config={"every": 3})
    # Dernier check-in complété avant-hier : 2 < 3 jours → pas dû.
    HabitCheckIn.objects.create(
        habit=habit, date=date.today() - timedelta(days=2), completed=True
    )
    HabitReminder.objects.create(habit=habit, time=PAST)
    assert habit_tasks.dispatch_habit_reminders() == 0

    # Le lendemain de l'intervalle (3 jours écoulés) → dû.
    HabitCheckIn.objects.filter(habit=habit).update(date=date.today() - timedelta(days=3))
    HabitReminder.objects.filter(habit=habit).update(last_sent_on=None)
    assert habit_tasks.dispatch_habit_reminders() == 1
