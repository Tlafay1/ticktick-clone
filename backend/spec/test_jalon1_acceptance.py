"""Jalon 1 — spec d'acceptation (tests RÉELS, doivent être verts).

Altitude acceptation : on vérifie que l'API couvre les besoins de l'UI,
notamment la composition des smart lists par query params. Couvre les
modules PRD 1, 2.1, 2.2, 3 (plat), 10 (recherche), 14, 25.1, 31, 33.
"""
from datetime import timedelta

import pytest
from django.utils import timezone

pytestmark = pytest.mark.spec


def mk(api, project_id, title="T", **extra):
    res = api.post("/api/tasks/", {"project": project_id, "title": title, **extra})
    assert res.status_code == 201, res.data
    return res.data


def iso(dt):
    return dt.isoformat()


# ---- Module 1 : moteur de tâches ----

def test_m01_task_core_fields_persist(api, inbox):
    """Une tâche stocke titre unicode, description markdown, priorité, dates,
    flag all-day et fuseau."""
    due = timezone.now() + timedelta(days=2)
    task = mk(
        api, inbox.id,
        title="Acheter du lait 🥛",
        description="- [ ] entier\n- [ ] demi-écrémé",
        priority=5,
        due_date=iso(due),
        is_all_day=False,
        timezone_name="Europe/Paris",
    )
    assert task["priority"] == 5
    assert task["is_all_day"] is False
    assert task["timezone_name"] == "Europe/Paris"
    assert "🥛" in task["title"]


def test_m01_subtask_tier1_lives_in_parent_project(api, inbox):
    """Une sous-tâche (Tier 1) hérite de la liste de son parent."""
    other = api.post("/api/projects/", {"name": "Autre"}).data
    parent = mk(api, inbox.id, "Parent")
    child = mk(api, other["id"], "Enfant", parent=parent["id"])
    assert child["project"] == inbox.id  # forcé sur la liste du parent


def test_m01_subtask_reparent_cycle_rejected(api, inbox):
    """Reparenter une tâche sous elle-même ou l'un de ses descendants → 400.

    Sans ce garde-fou, le cycle créé fait boucler à l'infini Task.depth et
    Task.descendants() au prochain complete/trash (auto-DoS).
    """
    a = mk(api, inbox.id, "A")
    b = mk(api, inbox.id, "B", parent=a["id"])
    c = mk(api, inbox.id, "C", parent=b["id"])

    # A ne peut devenir enfant ni d'elle-même, ni de son enfant, ni d'un
    # descendant plus profond.
    assert api.patch(f"/api/tasks/{a['id']}/", {"parent": a["id"]}).status_code == 400
    assert api.patch(f"/api/tasks/{a['id']}/", {"parent": b["id"]}).status_code == 400
    assert api.patch(f"/api/tasks/{a['id']}/", {"parent": c["id"]}).status_code == 400

    # Un reparentage légitime reste accepté (C remonte sous A).
    res = api.patch(f"/api/tasks/{c['id']}/", {"parent": a["id"]})
    assert res.status_code == 200
    assert res.data["parent"] == a["id"]


# ---- Module 2.1 : Inbox + listes ----

def test_m02_inbox_exists_and_is_protected(api, inbox):
    """L'Inbox est créée d'office, non supprimable, non renommable."""
    assert inbox.is_inbox
    assert api.delete(f"/api/projects/{inbox.id}/").status_code == 400
    assert api.patch(f"/api/projects/{inbox.id}/", {"name": "X"}).status_code == 400


def test_m02_custom_list_crud(api):
    p = api.post("/api/projects/", {"name": "Travail", "color": "#4772fa"}).data
    assert api.patch(f"/api/projects/{p['id']}/", {"name": "Boulot"}).data["name"] == "Boulot"
    assert api.delete(f"/api/projects/{p['id']}/").status_code == 204


# ---- Module 2.2 : smart lists par défaut (composées côté UI) ----

def test_m02_smartlist_today_shows_due_today_and_overdue(api, inbox):
    """Today = tâches dues aujourd'hui OU en retard, non terminées."""
    now = timezone.now()
    overdue = mk(api, inbox.id, "En retard", due_date=iso(now - timedelta(days=1)))
    today = mk(api, inbox.id, "Aujourd'hui", due_date=iso(now))
    mk(api, inbox.id, "Plus tard", due_date=iso(now + timedelta(days=3)))
    mk(api, inbox.id, "Sans date")

    end_today = (now.replace(hour=0, minute=0, second=0, microsecond=0)
                 + timedelta(days=1))
    res = api.get(
        "/api/tasks/",
        {"smart": 1, "status": 0, "due_before": iso(end_today)},
    ).data
    ids = {t["id"] for t in res}
    assert ids == {overdue["id"], today["id"]}


def test_m02_smartlist_next7days(api, inbox):
    now = timezone.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    inside = mk(api, inbox.id, "Dans 3j", due_date=iso(now + timedelta(days=3)))
    mk(api, inbox.id, "Dans 10j", due_date=iso(now + timedelta(days=10)))
    res = api.get(
        "/api/tasks/",
        {
            "smart": 1,
            "status": 0,
            "due_after": iso(start),
            "due_before": iso(start + timedelta(days=7)),
        },
    ).data
    assert {t["id"] for t in res} == {inside["id"]}


def test_m02_smartlist_completed_grouped_by_date(api, inbox):
    """Completed = vue plate des tâches terminées, triable par completed_at."""
    t = mk(api, inbox.id, "Fini")
    api.post(f"/api/tasks/{t['id']}/complete/")
    res = api.get("/api/tasks/?status=2&ordering=-completed_at").data
    assert [x["id"] for x in res] == [t["id"]]
    assert res[0]["completed_at"] is not None


def test_m02_smartlist_all_aggregates_across_lists(api, inbox):
    work = api.post("/api/projects/", {"name": "Work"}).data
    a = mk(api, inbox.id, "A")
    b = mk(api, work["id"], "B")
    res = api.get("/api/tasks/?smart=1").data
    assert {a["id"], b["id"]} <= {t["id"] for t in res}


# ---- Module 3 : tags plats ----

def test_m03_flat_tag_assign_and_filter(api, inbox):
    tag = api.post("/api/tags/", {"name": "courses", "color": "#fab005"}).data
    t = mk(api, inbox.id, "Lait", tags=[tag["id"]])
    mk(api, inbox.id, "Sans tag")
    res = api.get("/api/tasks/?tag=courses").data
    assert {x["id"] for x in res} == {t["id"]}


# ---- Module 10.2 : recherche ----

def test_m10_search_title_description_checkitems(api, inbox):
    a = mk(api, inbox.id, "Réunion budget piscine")
    b = mk(api, inbox.id, "Sport", description="aller à la piscine")
    c = mk(api, inbox.id, "Courses")
    api.post("/api/check-items/", {"task": c["id"], "title": "piscine gonflable"})
    ids = {t["id"] for t in api.get("/api/tasks/?q=piscine").data}
    assert ids == {a["id"], b["id"], c["id"]}


# ---- Module 14 : Won't Do ----

def test_m14_wont_do_is_distinct_third_state(api, inbox):
    t = mk(api, inbox.id, "Abandonné")
    api.post(f"/api/tasks/{t['id']}/wont-do/")
    got = api.get(f"/api/tasks/{t['id']}/").data
    assert got["status"] == -1 and got["completed_at"] is not None
    # N'apparaît ni dans les actives ni dans les terminées.
    assert t["id"] not in {x["id"] for x in api.get("/api/tasks/?status=0").data}
    assert t["id"] not in {x["id"] for x in api.get("/api/tasks/?status=2").data}
    assert t["id"] in {x["id"] for x in api.get("/api/tasks/?status=-1").data}


# ---- Module 25.1 : progression ----

def test_m25_progress_bounded_0_100(api, inbox):
    t = mk(api, inbox.id, "Complexe")
    assert api.patch(f"/api/tasks/{t['id']}/", {"progress": 60}).data["progress"] == 60
    assert api.patch(f"/api/tasks/{t['id']}/", {"progress": 140}).status_code == 400


def test_m25_completion_forces_progress_100(api, inbox):
    t = mk(api, inbox.id, "X", progress=30)
    api.post(f"/api/tasks/{t['id']}/complete/")
    assert api.get(f"/api/tasks/{t['id']}/").data["progress"] == 100


# ---- Module 31 : 3 tiers de checklist ----

def test_m31_tier1_subtasks_and_tier2_checkitems_coexist(api, inbox):
    """Tier 1 = vraies sous-tâches (parent), Tier 2 = check items légers.
    Tier 3 (checkboxes markdown) est purement front (cf. vitest markdown)."""
    parent = mk(api, inbox.id, "Tâche riche")
    sub = mk(api, inbox.id, "Sous-tâche planifiable", parent=parent["id"],
             due_date=iso(timezone.now()))
    ci = api.post("/api/check-items/", {"task": parent["id"], "title": "item léger"}).data
    detail = api.get(f"/api/tasks/{parent['id']}/").data
    assert detail["check_items"][0]["id"] == ci["id"]
    assert sub["due_date"] is not None  # Tier 1 peut avoir sa propre date
    children = api.get(f"/api/tasks/?parent={parent['id']}").data
    assert [c["id"] for c in children] == [sub["id"]]


def test_m31_checkitem_autosorts_to_bottom_when_done(api, inbox):
    t = mk(api, inbox.id, "X")
    a = api.post("/api/check-items/", {"task": t["id"], "title": "a", "sort_order": 0}).data
    api.post("/api/check-items/", {"task": t["id"], "title": "b", "sort_order": 1})
    api.patch(f"/api/check-items/{a['id']}/", {"is_done": True})
    items = api.get(f"/api/tasks/{t['id']}/").data["check_items"]
    assert [i["title"] for i in items] == ["b", "a"]


# ---- Module 33 : commentaires horodatés ----

def test_m33_comment_keeps_created_marks_edited(api, inbox):
    t = mk(api, inbox.id, "X")
    c = api.post("/api/comments/", {"task": t["id"], "content": "v1"}).data
    assert c["edited_at"] is None
    up = api.patch(f"/api/comments/{c['id']}/", {"content": "v2"}).data
    assert up["created_at"] == c["created_at"] and up["edited_at"] is not None


# ---- Module 1.2 : actions de tâche ----

def test_m01_actions_pin_postpone_duplicate_trash(api, inbox):
    t = mk(api, inbox.id, "X")
    # Épingler
    assert api.patch(f"/api/tasks/{t['id']}/", {"is_pinned": True}).data["pinned_at"]
    # Reporter (presets côté UI → PATCH due_date)
    tomorrow = timezone.now() + timedelta(days=1)
    assert api.patch(f"/api/tasks/{t['id']}/", {"due_date": iso(tomorrow)}).data["due_date"]
    # Dupliquer
    copy = api.post(f"/api/tasks/{t['id']}/duplicate/").data
    assert copy["title"] == "X (copy)" and copy["id"] != t["id"]
    # Corbeille puis restauration
    api.delete(f"/api/tasks/{t['id']}/")
    assert t["id"] not in {x["id"] for x in api.get("/api/tasks/").data}
    api.post(f"/api/tasks/{t['id']}/restore/")
    assert t["id"] in {x["id"] for x in api.get("/api/tasks/").data}
