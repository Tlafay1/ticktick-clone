from datetime import timedelta

import pytest
from django.utils import timezone

from apps.tasks.models import Task

pytestmark = pytest.mark.django_db


def make_task(api, inbox, title="Tâche", **extra):
    res = api.post("/api/tasks/", {"project": inbox.id, "title": title, **extra})
    assert res.status_code == 201, res.data
    return res.data


def test_create_task_minimal(api, inbox):
    task = make_task(api, inbox, title="Acheter du lait 🥛", priority=5)
    assert task["status"] == 0
    assert task["priority"] == 5
    activity = api.get(f"/api/tasks/{task['id']}/activity/").data
    assert activity[0]["action"] == "created"


def test_complete_cascades_to_children(api, inbox):
    parent = make_task(api, inbox, title="Parent")
    child = make_task(api, inbox, title="Enfant", parent=parent["id"])
    api.post(f"/api/tasks/{parent['id']}/complete/")
    assert api.get(f"/api/tasks/{child['id']}/").data["status"] == 2


def test_completing_all_children_completes_parent(api, inbox):
    parent = make_task(api, inbox, title="Parent")
    c1 = make_task(api, inbox, title="A", parent=parent["id"])
    c2 = make_task(api, inbox, title="B", parent=parent["id"])
    api.post(f"/api/tasks/{c1['id']}/complete/")
    assert api.get(f"/api/tasks/{parent['id']}/").data["status"] == 0
    api.post(f"/api/tasks/{c2['id']}/complete/")
    assert api.get(f"/api/tasks/{parent['id']}/").data["status"] == 2


def test_wont_do_and_reopen(api, inbox):
    task = make_task(api, inbox)
    api.post(f"/api/tasks/{task['id']}/wont-do/")
    assert api.get(f"/api/tasks/{task['id']}/").data["status"] == -1
    api.post(f"/api/tasks/{task['id']}/reopen/")
    assert api.get(f"/api/tasks/{task['id']}/").data["status"] == 0


def test_subtask_depth_limit(api, inbox):
    parent = make_task(api, inbox, title="N0")
    for i in range(1, 5):
        parent = make_task(api, inbox, title=f"N{i}", parent=parent["id"])
    res = api.post(
        "/api/tasks/", {"project": inbox.id, "title": "Trop profond", "parent": parent["id"]}
    )
    assert res.status_code == 400


def test_trash_restore_and_empty(api, inbox):
    parent = make_task(api, inbox, title="Parent")
    child = make_task(api, inbox, title="Enfant", parent=parent["id"])
    api.delete(f"/api/tasks/{parent['id']}/")  # → corbeille, avec l'enfant

    active = api.get("/api/tasks/").data
    assert {t["id"] for t in active} == set()
    trash = api.get("/api/tasks/?trashed=1").data
    assert {t["id"] for t in trash} == {parent["id"], child["id"]}

    api.post(f"/api/tasks/{parent['id']}/restore/")
    assert {t["id"] for t in api.get("/api/tasks/").data} == {parent["id"], child["id"]}

    api.delete(f"/api/tasks/{parent['id']}/")
    api.post("/api/tasks/empty-trash/")
    assert api.get("/api/tasks/?trashed=1").data == []
    assert api.get(f"/api/tasks/{parent['id']}/").status_code == 404


def test_trash_purges_after_30_days(api, inbox, user):
    task = make_task(api, inbox)
    api.delete(f"/api/tasks/{task['id']}/")
    Task.objects.filter(pk=task["id"]).update(
        trashed_at=timezone.now() - timedelta(days=31)
    )
    assert api.get("/api/tasks/?trashed=1").data == []


def test_duplicate_with_children_and_checklist(api, inbox):
    parent = make_task(api, inbox, title="Voyage")
    make_task(api, inbox, title="Valise", parent=parent["id"])
    api.post("/api/check-items/", {"task": parent["id"], "title": "Passeport"})
    copy = api.post(f"/api/tasks/{parent['id']}/duplicate/").data
    assert copy["title"] == "Voyage (copy)"
    assert len(copy["check_items"]) == 1
    children = api.get(f"/api/tasks/?parent={copy['id']}").data
    assert [c["title"] for c in children] == ["Valise"]


def test_check_item_done_moves_bottom_and_timestamps(api, inbox):
    task = make_task(api, inbox)
    a = api.post("/api/check-items/", {"task": task["id"], "title": "a", "sort_order": 0}).data
    b = api.post("/api/check-items/", {"task": task["id"], "title": "b", "sort_order": 1}).data
    api.patch(f"/api/check-items/{a['id']}/", {"is_done": True})
    items = api.get(f"/api/tasks/{task['id']}/").data["check_items"]
    assert [i["title"] for i in items] == ["b", "a"]  # l'item coché passe en bas
    assert items[1]["completed_at"] is not None


def test_smart_filter_excludes_hidden_lists(api, user, inbox):
    hidden = api.post(
        "/api/projects/", {"name": "Vault", "hidden_from_smart_lists": True}
    ).data
    make_task(api, inbox, title="Visible")
    res = api.post("/api/tasks/", {"project": hidden["id"], "title": "Cachée"})
    assert res.status_code == 201
    titles = [t["title"] for t in api.get("/api/tasks/?smart=1").data]
    assert titles == ["Visible"]
    # Mais la liste reste consultable directement.
    titles = [t["title"] for t in api.get(f"/api/tasks/?project={hidden['id']}").data]
    assert titles == ["Cachée"]


def test_search_in_title_description_checkitems(api, inbox):
    t1 = make_task(api, inbox, title="Réunion budget")
    make_task(api, inbox, title="Sport", description="aller à la piscine")
    t3 = make_task(api, inbox, title="Courses")
    api.post("/api/check-items/", {"task": t3["id"], "title": "piscine gonflable"})
    ids = {t["id"] for t in api.get("/api/tasks/?q=piscine").data}
    assert t1["id"] not in ids and len(ids) == 2


def test_postpone_via_patch_and_pin(api, inbox):
    task = make_task(api, inbox)
    due = (timezone.now() + timedelta(days=1)).isoformat()
    res = api.patch(f"/api/tasks/{task['id']}/", {"due_date": due, "is_pinned": True})
    assert res.data["due_date"] is not None
    assert res.data["pinned_at"] is not None
    activity = api.get(f"/api/tasks/{task['id']}/activity/").data
    assert any(a["action"] == "updated" for a in activity)


def test_comments_edited_marker(api, inbox):
    task = make_task(api, inbox)
    c = api.post("/api/comments/", {"task": task["id"], "content": "premier jet"}).data
    assert c["edited_at"] is None
    updated = api.patch(f"/api/comments/{c['id']}/", {"content": "corrigé"}).data
    assert updated["edited_at"] is not None
    assert updated["created_at"] == c["created_at"]
