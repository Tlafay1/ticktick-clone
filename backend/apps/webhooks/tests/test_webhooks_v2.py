"""Webhooks v2 : enveloppe enrichie, diff, acteur, retries, nouveaux événements."""
import urllib.error
from contextlib import contextmanager

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def captured(monkeypatch):
    calls = []
    monkeypatch.setattr("apps.webhooks.tasks.deliver_webhook.delay",
                        lambda *args: calls.append(args))
    return calls


def envelopes(calls):
    return [c[1] for c in calls]


# --- Enveloppe : acteur + diff sur update ----------------------------------

def test_update_inclut_acteur_et_diff(api, inbox, captured):
    from apps.webhooks.models import Webhook

    Webhook.objects.create(user=inbox.user, url="https://x/h", events=["task.updated"])
    task = api.post("/api/tasks/", {"project": inbox.id, "title": "avant"},
                    format="json").json()
    api.patch(f"/api/tasks/{task['id']}/", {"title": "après"},
              format="json", HTTP_X_ACTOR="agent:z")
    env = next(e for e in envelopes(captured) if e["event"] == "task.updated")
    assert env["actor"] == "agent:z"
    assert env["changes"]["title"] == {"old": "avant", "new": "après"}
    assert env["id"] and env["timestamp"]


def test_deleted_envoie_snapshot_complet(api, inbox, captured):
    from apps.webhooks.models import Webhook

    Webhook.objects.create(user=inbox.user, url="https://x/h", events=["task.deleted"])
    task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"},
                    format="json").json()
    api.delete(f"/api/tasks/{task['id']}/?permanent=1")
    env = next(e for e in envelopes(captured) if e["event"] == "task.deleted")
    assert env["data"]["title"] == "T"  # snapshot, pas seulement {id}
    assert env["data"]["id"] == task["id"]


# --- Nouveaux événements ----------------------------------------------------

def test_project_events(api, inbox, captured):
    from apps.webhooks.models import Webhook

    Webhook.objects.create(user=inbox.user, url="https://x/h", events=[])
    p = api.post("/api/projects/", {"name": "P"}, format="json").json()
    api.patch(f"/api/projects/{p['id']}/", {"name": "P2"}, format="json")
    api.delete(f"/api/projects/{p['id']}/")
    evs = [e["event"] for e in envelopes(captured)]
    assert {"project.created", "project.updated", "project.deleted"} <= set(evs)


def test_habit_checkin_event(api, inbox, captured):
    from apps.webhooks.models import Webhook

    Webhook.objects.create(user=inbox.user, url="https://x/h", events=["habit.checkin"])
    habit = api.post("/api/habits/", {"name": "Eau"}, format="json").json()
    api.post(f"/api/habits/{habit['id']}/checkins/", {"date": "2026-07-14"}, format="json")
    assert any(e["event"] == "habit.checkin" for e in envelopes(captured))


def test_catalogue_expose_nouveaux_events(api):
    events = api.get("/api/webhooks/events/").json()["events"]
    for e in ["task.claimed", "project.created", "habit.checkin",
              "pomodoro.started", "pomodoro.completed"]:
        assert e in events


# --- Fiabilité : retry avec backoff ----------------------------------------

def test_retry_sur_echec_reseau(inbox, monkeypatch):
    from apps.webhooks.dispatch import build_envelope
    from apps.webhooks.models import Webhook, WebhookDelivery
    from apps.webhooks import tasks as wtasks

    hook = Webhook.objects.create(user=inbox.user, url="https://x/h")

    @contextmanager
    def boom(request, timeout=None):
        raise urllib.error.URLError("réseau coupé")
        yield  # pragma: no cover

    monkeypatch.setattr("urllib.request.urlopen", boom)

    retried = {}
    def fake_retry(self, exc=None):
        retried["called"] = True
        raise RuntimeError("retry planifié")
    monkeypatch.setattr(wtasks.deliver_webhook, "retry", fake_retry.__get__(wtasks.deliver_webhook))

    envelope = build_envelope("task.created", {"id": 1})
    with pytest.raises(RuntimeError):
        wtasks.deliver_webhook.apply(args=[hook.id, envelope], throw=True).get()

    assert retried.get("called") is True
    delivery = WebhookDelivery.objects.get(webhook=hook)
    assert delivery.success is False and delivery.error


def test_config_retry_backoff():
    from apps.webhooks.tasks import deliver_webhook

    assert deliver_webhook.max_retries == 5
    assert deliver_webhook.retry_backoff is True
