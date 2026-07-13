"""Webhooks : CRUD, déclenchement sur événements de tâche, livraison signée."""
import hashlib
import hmac
import json
from contextlib import contextmanager

import pytest

pytestmark = pytest.mark.django_db


# --- CRUD -------------------------------------------------------------------

def test_create_webhook_generates_secret(api):
    resp = api.post(
        "/api/webhooks/",
        {"url": "https://n8n.example/hook", "events": ["task.created"]},
        format="json",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["secret"]  # généré et renvoyé une fois
    assert body["events"] == ["task.created"]


def test_reject_unknown_event(api):
    resp = api.post(
        "/api/webhooks/",
        {"url": "https://x/hook", "events": ["task.exploded"]},
        format="json",
    )
    assert resp.status_code == 400


def test_events_catalogue(api):
    resp = api.get("/api/webhooks/events/")
    assert "task.completed" in resp.json()["events"]


def test_isolation(api, django_user_model):
    from apps.webhooks.models import Webhook

    other = django_user_model.objects.create_user(email="o@x.com", password="x")
    hook = Webhook.objects.create(user=other, url="https://x/h")
    assert api.get(f"/api/webhooks/{hook.id}/").status_code == 404


# --- Déclenchement (emit) ---------------------------------------------------

@pytest.fixture
def captured_deliveries(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "apps.webhooks.tasks.deliver_webhook.delay",
        lambda *args: calls.append(args),
    )
    return calls


def test_task_created_triggers_matching_webhook(api, inbox, captured_deliveries):
    from apps.webhooks.models import Webhook

    hook = Webhook.objects.create(user=inbox.user, url="https://x/h", events=[])
    api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json")
    assert any(c[0] == hook.id and c[1] == "task.created" for c in captured_deliveries)


def test_event_filter_is_respected(api, inbox, captured_deliveries):
    from apps.webhooks.models import Webhook

    Webhook.objects.create(user=inbox.user, url="https://x/h", events=["task.completed"])
    task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json").json()
    assert captured_deliveries == []  # création ignorée

    api.post(f"/api/tasks/{task['id']}/complete/")
    assert any(c[1] == "task.completed" for c in captured_deliveries)


def test_inactive_webhook_not_triggered(api, inbox, captured_deliveries):
    from apps.webhooks.models import Webhook

    Webhook.objects.create(user=inbox.user, url="https://x/h", is_active=False)
    api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json")
    assert captured_deliveries == []


def test_task_deleted_emits(api, inbox, captured_deliveries):
    task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json").json()
    from apps.webhooks.models import Webhook

    Webhook.objects.create(user=inbox.user, url="https://x/h", events=["task.deleted"])
    api.delete(f"/api/tasks/{task['id']}/?permanent=1")
    assert any(c[1] == "task.deleted" for c in captured_deliveries)


# --- Livraison signée -------------------------------------------------------

def test_delivery_signs_body_and_logs(api, inbox, monkeypatch):
    from apps.webhooks.models import Webhook, WebhookDelivery
    from apps.webhooks.tasks import deliver_webhook

    hook = Webhook.objects.create(user=inbox.user, url="https://x/h", secret="s3cr3t")

    seen = {}

    @contextmanager
    def fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["body"] = request.data
        seen["sig"] = request.headers.get("X-webhook-signature")
        seen["event"] = request.headers.get("X-webhook-event")

        class Resp:
            status = 200

        yield Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = deliver_webhook.apply(args=[hook.id, "task.created", {"id": 1}]).get()

    assert result == 200
    expected = hmac.new(b"s3cr3t", seen["body"], hashlib.sha256).hexdigest()
    assert seen["sig"] == f"sha256={expected}"
    assert seen["event"] == "task.created"
    assert json.loads(seen["body"]) == {"event": "task.created", "data": {"id": 1}}
    delivery = WebhookDelivery.objects.get(webhook=hook)
    assert delivery.success is True and delivery.status_code == 200
