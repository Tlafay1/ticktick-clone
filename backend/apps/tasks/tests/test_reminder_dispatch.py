"""Dispatch serveur des rappels de tâches (Web Push) : idempotence, robustesse, réarmement."""

from datetime import datetime, timedelta
from datetime import timezone as dt_tz

import pytest

from apps.tasks import tasks as task_jobs
from apps.tasks.models import Reminder, Task

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 10, 7, 18, 0, tzinfo=dt_tz.utc)


@pytest.fixture
def now(monkeypatch):
    """Horloge pilotable : `now.set(dt)` avance le temps vu par le dispatch."""

    class Clock:
        value = NOW

        def set(self, dt):
            self.value = dt

    clock = Clock()
    monkeypatch.setattr("django.utils.timezone.now", lambda: clock.value)
    return clock


@pytest.fixture
def pushes(monkeypatch):
    """Web Push capturé ; FCM neutralisé (couvert par accounts/tests/test_fcm.py)."""
    calls = []

    def fake_push(user, title, body, url, tag=""):
        calls.append({"title": title, "url": url, "tag": tag})

    monkeypatch.setattr(task_jobs, "notify_user", fake_push)
    monkeypatch.setattr(task_jobs, "send_fcm", lambda *a, **kw: 0)
    return calls


def _task(user, inbox, **kw):
    kw.setdefault("due_date", NOW)
    return Task.objects.create(user=user, project=inbox, title="Appeler l'agence", **kw)


def test_due_reminder_sent_once_with_shared_tag(user, inbox, now, pushes):
    task = _task(user, inbox)
    reminder = Reminder.objects.create(task=task, minutes_before=0)

    assert task_jobs.dispatch_due_reminders() == 1
    assert pushes == [{
        "title": "Appeler l'agence",
        "url": f"/task/{task.id}",
        "tag": f"reminder-{reminder.id}-{int(NOW.timestamp())}",
    }]
    # Idempotent : un second passage n'envoie rien.
    assert task_jobs.dispatch_due_reminders() == 0
    assert len(pushes) == 1


def test_future_reminder_waits(user, inbox, now, pushes):
    Reminder.objects.create(task=_task(user, inbox), minutes_before=0)
    now.set(NOW - timedelta(minutes=1))
    assert task_jobs.dispatch_due_reminders() == 0
    assert pushes == []


def test_failing_channel_does_not_loop_nor_block_others(user, inbox, now, monkeypatch):
    """Régression « rappels en boucle » : un envoi qui lève marquait jamais le rappel."""
    first = Reminder.objects.create(task=_task(user, inbox), minutes_before=0)
    second = Reminder.objects.create(task=_task(user, inbox), minutes_before=0)
    calls = []

    def flaky_push(user, title, body, url, tag=""):
        calls.append(tag)
        if len(calls) == 1:
            raise RuntimeError("service push indisponible")

    monkeypatch.setattr(task_jobs, "notify_user", flaky_push)
    monkeypatch.setattr(task_jobs, "send_fcm", lambda *a, **kw: 0)
    task_jobs.dispatch_due_reminders()
    assert len(calls) == 2  # le second rappel n'est pas bloqué par le premier
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.dispatched_at is not None and second.dispatched_at is not None
    # Minute suivante : rien n'est renvoyé.
    now.set(NOW + timedelta(minutes=1))
    task_jobs.dispatch_due_reminders()
    assert len(calls) == 2


def test_recurring_task_rearms_reminder_for_next_occurrence(user, inbox, now, pushes):
    task = _task(user, inbox, rrule="FREQ=DAILY")
    Reminder.objects.create(task=task, minutes_before=10)
    now.set(NOW - timedelta(minutes=10))
    assert task_jobs.dispatch_due_reminders() == 1

    task.set_status(Task.Status.COMPLETED)  # avance l'échéance au lendemain
    task.refresh_from_db()
    assert task.due_date == NOW + timedelta(days=1)

    now.set(NOW + timedelta(days=1, minutes=-10))
    assert task_jobs.dispatch_due_reminders() == 1
    assert len(pushes) == 2
    assert pushes[0]["tag"] != pushes[1]["tag"]


def test_postponed_task_rearms_reminder(user, inbox, now, pushes):
    task = _task(user, inbox)
    Reminder.objects.create(task=task, minutes_before=0)
    task_jobs.dispatch_due_reminders()

    task.due_date = NOW + timedelta(hours=3)
    task.save()
    now.set(NOW + timedelta(hours=3))
    assert task_jobs.dispatch_due_reminders() == 1


def test_stale_reminder_marked_without_notifying(user, inbox, now, pushes):
    """Après une panne, les rappels vieux de plus de 2 h ne partent pas en rafale."""
    reminder = Reminder.objects.create(task=_task(user, inbox), minutes_before=0)
    now.set(NOW + timedelta(hours=3))
    assert task_jobs.dispatch_due_reminders() == 0
    assert pushes == []
    reminder.refresh_from_db()
    assert reminder.dispatched_at is not None


def test_completed_and_trashed_tasks_skipped(user, inbox, now, pushes):
    done = _task(user, inbox, status=Task.Status.COMPLETED)
    trashed = _task(user, inbox, trashed_at=NOW)
    Reminder.objects.create(task=done, minutes_before=0)
    Reminder.objects.create(task=trashed, minutes_before=0)
    assert task_jobs.dispatch_due_reminders() == 0
    assert pushes == []
