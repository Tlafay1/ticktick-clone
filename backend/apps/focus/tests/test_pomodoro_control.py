"""Sessions de focus pilotées serveur : start / stop / current + événements."""
import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def hook_calls(monkeypatch, inbox):
    from apps.webhooks.models import Webhook

    Webhook.objects.create(user=inbox.user, url="https://x/h", events=[])
    calls = []
    monkeypatch.setattr("apps.webhooks.tasks.deliver_webhook.delay",
                        lambda *a: calls.append(a))
    return calls


def events(calls):
    return [c[1]["event"] for c in calls]


def test_start_cree_session_en_cours(api, inbox, hook_calls):
    res = api.post("/api/focus-sessions/start/", {"planned_seconds": 1500}, format="json")
    assert res.status_code == 201
    assert res.data["end_at"] is None
    assert res.data["planned_seconds"] == 1500
    assert "pomodoro.started" in events(hook_calls)


def test_start_refuse_si_deja_en_cours(api, inbox):
    api.post("/api/focus-sessions/start/", {}, format="json")
    res = api.post("/api/focus-sessions/start/", {}, format="json")
    assert res.status_code == 409


def test_current_reflete_l_etat(api, inbox):
    assert api.get("/api/focus-sessions/current/").status_code == 204
    api.post("/api/focus-sessions/start/", {}, format="json")
    res = api.get("/api/focus-sessions/current/")
    assert res.status_code == 200 and res.data["end_at"] is None


def test_stop_clot_et_calcule_duree(api, inbox, hook_calls):
    api.post("/api/focus-sessions/start/", {}, format="json")
    res = api.post("/api/focus-sessions/stop/", {}, format="json")
    assert res.status_code == 200
    assert res.data["end_at"] is not None
    assert res.data["duration_seconds"] >= 0
    # sans planned_seconds la session est considérée complétée
    assert "pomodoro.completed" in events(hook_calls)
    assert api.get("/api/focus-sessions/current/").status_code == 204


def test_stop_avant_duree_prevue_emet_stopped(api, inbox, hook_calls):
    api.post("/api/focus-sessions/start/", {"planned_seconds": 99999}, format="json")
    api.post("/api/focus-sessions/stop/", {}, format="json")
    evs = events(hook_calls)
    assert "pomodoro.stopped" in evs
    assert "pomodoro.completed" not in evs


def test_stop_sans_session_409(api, inbox):
    assert api.post("/api/focus-sessions/stop/", {}, format="json").status_code == 409


def test_start_task_d_autrui_refuse(api, inbox, django_user_model):
    other = django_user_model.objects.create_user(email="o@x.com", password="x")
    from apps.tasks.models import Task

    foreign = Task.objects.create(user=other,
                                  project=other.projects.get(is_inbox=True), title="X")
    res = api.post("/api/focus-sessions/start/", {"task": foreign.id}, format="json")
    assert res.status_code == 400


def test_historique_filtre_par_date(api, inbox):
    from datetime import timedelta
    from urllib.parse import quote

    from django.utils import timezone

    api.post("/api/focus-sessions/start/", {}, format="json")
    api.post("/api/focus-sessions/stop/", {}, format="json")
    past = quote((timezone.now() - timedelta(days=1)).isoformat())
    res = api.get(f"/api/focus-sessions/?start_after={past}")
    assert res.status_code == 200 and len(res.data) == 1
