"""API dédiée aux agents IA : acteur, requêtes agrégées, bulk, claim, rrule null."""
from datetime import timedelta

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


def mk(api, project_id, title="T", **extra):
    res = api.post("/api/tasks/", {"project": project_id, "title": title, **extra},
                   format="json")
    assert res.status_code == 201, res.data
    return res.data


# --- Attribution d'acteur (X-Actor) ----------------------------------------

def test_actor_defaut_user(api, inbox):
    t = mk(api, inbox.id)
    assert t["last_actor"] == "user"


def test_actor_depuis_header_a_la_creation(api, inbox):
    res = api.post("/api/tasks/", {"project": inbox.id, "title": "T"},
                   format="json", HTTP_X_ACTOR="agent:gemini")
    assert res.data["last_actor"] == "agent:gemini"


def test_actor_sur_update_et_activity(api, inbox):
    t = mk(api, inbox.id)
    api.patch(f"/api/tasks/{t['id']}/", {"title": "modifié"},
              format="json", HTTP_X_ACTOR="agent:worker")
    fresh = api.get(f"/api/tasks/{t['id']}/").data
    assert fresh["last_actor"] == "agent:worker"
    logs = api.get(f"/api/tasks/{t['id']}/activity/").data
    assert any(log["actor"] == "agent:worker" for log in logs)


def test_actor_sur_complete(api, inbox):
    t = mk(api, inbox.id)
    api.post(f"/api/tasks/{t['id']}/complete/", HTTP_X_ACTOR="agent:x")
    assert api.get(f"/api/tasks/{t['id']}/").data["last_actor"] == "agent:x"


# --- rrule "" -> null -------------------------------------------------------

def test_rrule_vide_serialise_null(api, inbox):
    t = mk(api, inbox.id)
    assert t["rrule"] is None  # jamais "" (bug historique corrigé)


def test_rrule_null_accepte_en_entree(api, inbox):
    t = mk(api, inbox.id, rrule="FREQ=DAILY")
    assert t["rrule"] == "FREQ=DAILY"
    res = api.patch(f"/api/tasks/{t['id']}/", {"rrule": None}, format="json")
    assert res.status_code == 200, res.data
    assert api.get(f"/api/tasks/{t['id']}/").data["rrule"] is None


# --- claimed_by + task.claimed ---------------------------------------------

def test_claimed_by_defaut_null(api, inbox):
    assert mk(api, inbox.id)["claimed_by"] is None


def test_claim_task_emet_event(api, inbox, monkeypatch):
    from apps.webhooks.models import Webhook

    Webhook.objects.create(user=inbox.user, url="https://x/h", events=["task.claimed"])
    calls = []
    monkeypatch.setattr("apps.webhooks.tasks.deliver_webhook.delay",
                        lambda *a: calls.append(a))
    t = mk(api, inbox.id)
    api.patch(f"/api/tasks/{t['id']}/", {"claimed_by": "agent:owner"}, format="json")
    assert api.get(f"/api/tasks/{t['id']}/").data["claimed_by"] == "agent:owner"
    assert any(c[1]["event"] == "task.claimed" for c in calls)


# --- overdue / today / density ---------------------------------------------

def test_filtre_overdue(api, inbox):
    past = mk(api, inbox.id, "passé",
              due_date=(timezone.now() - timedelta(days=1)).isoformat())
    mk(api, inbox.id, "futur",
       due_date=(timezone.now() + timedelta(days=1)).isoformat())
    ids = [t["id"] for t in api.get("/api/tasks/?overdue=1").data]
    assert past["id"] in ids
    assert len(ids) == 1


def test_endpoint_today(api, inbox):
    now = timezone.now()
    mk(api, inbox.id, "retard", due_date=(now - timedelta(days=2)).isoformat())
    mk(api, inbox.id, "aujourdhui", due_date=(now + timedelta(hours=1)).isoformat())
    mk(api, inbox.id, "demain", due_date=(now + timedelta(days=2)).isoformat())
    data = api.get("/api/tasks/today/").data
    assert len(data["overdue"]) == 1
    assert len(data["today"]) == 1
    assert "date" in data


def test_endpoint_density(api, inbox):
    now = timezone.now()
    mk(api, inbox.id, "j+1", due_date=(now + timedelta(days=1, hours=1)).isoformat())
    mk(api, inbox.id, "j+1 bis", due_date=(now + timedelta(days=1, hours=2)).isoformat())
    data = api.get("/api/tasks/density/?days=5").data
    assert len(data) == 5
    total = sum(row["count"] for row in data)
    assert total == 2


# --- bulk -------------------------------------------------------------------

def test_bulk_complete(api, inbox):
    a, b = mk(api, inbox.id, "A"), mk(api, inbox.id, "B")
    res = api.post("/api/tasks/bulk/",
                   {"action": "complete", "ids": [a["id"], b["id"]]}, format="json")
    assert res.status_code == 200
    assert all(r["ok"] for r in res.data["results"])
    assert api.get(f"/api/tasks/{a['id']}/").data["status"] == 2


def test_bulk_resultat_par_item(api, inbox):
    a = mk(api, inbox.id, "A")
    res = api.post("/api/tasks/bulk/",
                   {"action": "complete", "ids": [a["id"], 999999]}, format="json")
    results = {r["id"]: r["ok"] for r in res.data["results"]}
    assert results[a["id"]] is True
    assert results[999999] is False  # pas de tout-ou-rien : l'un passe, l'autre échoue


def test_bulk_reschedule(api, inbox):
    a = mk(api, inbox.id, "A")
    new_due = (timezone.now() + timedelta(days=3)).replace(microsecond=0)
    res = api.post("/api/tasks/bulk/", {
        "action": "reschedule", "ids": [a["id"]],
        "data": {"due_date": new_due.isoformat()},
    }, format="json")
    assert res.status_code == 200 and res.data["results"][0]["ok"]
    from apps.tasks.serializers import TaskSerializer  # noqa: F401
    fresh = api.get(f"/api/tasks/{a['id']}/").data
    assert fresh["due_date"] is not None


def test_bulk_isolation(api, inbox, django_user_model):
    other = django_user_model.objects.create_user(email="o@x.com", password="x")
    from apps.tasks.models import Task

    foreign = Task.objects.create(user=other,
                                  project=other.projects.get(is_inbox=True), title="X")
    res = api.post("/api/tasks/bulk/",
                   {"action": "complete", "ids": [foreign.id]}, format="json")
    assert res.data["results"][0]["ok"] is False  # tâche d'autrui = introuvable
    foreign.refresh_from_db()
    assert foreign.status == 0
