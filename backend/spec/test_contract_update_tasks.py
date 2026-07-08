"""Contrat serveur des updates de tâches — PATCH /api/tasks/{id}/.

Moitié in-repo d'un fix cross-repo : l'assistant IA du repo frère (konofan)
pilote ce backend via API-Key et doit pouvoir mettre à jour dates, rappels,
parent et description en PATCH. Ces tests FIGENT le contrat : chaque champ
est accepté ET réellement persisté (relecture via GET, jamais le simple écho
de la réponse). Ne pas affaiblir sans coordonner le client konofan.
"""
from datetime import datetime, timedelta

import pytest
from django.utils import timezone

pytestmark = pytest.mark.spec


def mk(api, project_id, title="T", **extra):
    res = api.post("/api/tasks/", {"project": project_id, "title": title, **extra},
                   format="json")
    assert res.status_code == 201, res.data
    return res.data


def get(api, task_id):
    res = api.get(f"/api/tasks/{task_id}/")
    assert res.status_code == 200
    return res.data


def dt(value):
    """Parse un datetime DRF (suffixe Z ou offset) en datetime aware."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_patch_persiste_due_date_et_start_date(api, inbox):
    """due_date et start_date sont acceptés en PATCH, persistés, et effaçables."""
    t = mk(api, inbox.id)
    start = (timezone.now() + timedelta(days=1)).replace(microsecond=0)
    due = start + timedelta(days=2)

    res = api.patch(f"/api/tasks/{t['id']}/", {
        "start_date": start.isoformat(),
        "due_date": due.isoformat(),
    }, format="json")
    assert res.status_code == 200, res.data

    fresh = get(api, t["id"])
    assert dt(fresh["start_date"]) == start
    assert dt(fresh["due_date"]) == due

    # Effacement : null est accepté et persiste.
    res = api.patch(f"/api/tasks/{t['id']}/", {"due_date": None}, format="json")
    assert res.status_code == 200, res.data
    assert get(api, t["id"])["due_date"] is None


def test_patch_reminders_remplacement_complet(api, inbox):
    """`reminders` en PATCH remplace l'ensemble des rappels (delete puis
    recrée — cf. _save_reminders), et [] les efface tous."""
    t = mk(api, inbox.id, reminders=[
        {"trigger_type": "relative", "minutes_before": 5},
        {"trigger_type": "relative", "minutes_before": 30},
    ])
    assert len(get(api, t["id"])["reminders"]) == 2

    res = api.patch(f"/api/tasks/{t['id']}/", {
        "reminders": [{"trigger_type": "relative", "minutes_before": 60,
                       "annoying": True}],
    }, format="json")
    assert res.status_code == 200, res.data

    reminders = get(api, t["id"])["reminders"]
    assert len(reminders) == 1  # les 2 anciens ont disparu
    assert reminders[0]["minutes_before"] == 60
    assert reminders[0]["annoying"] is True

    # Remplacement par liste vide = suppression de tous les rappels.
    res = api.patch(f"/api/tasks/{t['id']}/", {"reminders": []}, format="json")
    assert res.status_code == 200, res.data
    assert get(api, t["id"])["reminders"] == []


def test_patch_persiste_parent(api, inbox):
    """`parent` est acceptée en PATCH : rattachement (avec alignement sur la
    liste du parent) et détachement (null)."""
    parent = mk(api, inbox.id, "Parent")
    child = mk(api, inbox.id, "Enfant")

    res = api.patch(f"/api/tasks/{child['id']}/", {"parent": parent["id"]},
                    format="json")
    assert res.status_code == 200, res.data
    fresh = get(api, child["id"])
    assert fresh["parent"] == parent["id"]
    assert fresh["project"] == inbox.id  # une sous-tâche vit dans la liste du parent

    res = api.patch(f"/api/tasks/{child['id']}/", {"parent": None}, format="json")
    assert res.status_code == 200, res.data
    assert get(api, child["id"])["parent"] is None


def test_patch_persiste_description(api, inbox):
    """`description` est acceptée en PATCH et persistée."""
    t = mk(api, inbox.id, description="Avant")
    res = api.patch(f"/api/tasks/{t['id']}/", {"description": "- [ ] Après"},
                    format="json")
    assert res.status_code == 200, res.data
    assert get(api, t["id"])["description"] == "- [ ] Après"
