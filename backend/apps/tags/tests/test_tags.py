import pytest

pytestmark = pytest.mark.django_db


def test_tag_crud_and_nesting(api):
    work = api.post("/api/tags/", {"name": "#Work", "color": "#ff0000"}).data
    assert work["name"] == "Work"  # le # est normalisé
    sub = api.post("/api/tags/", {"name": "Marketing", "parent": work["id"]}).data
    assert sub["parent"] == work["id"]


def test_tag_merge_moves_tasks_and_children(api, inbox):
    a = api.post("/api/tags/", {"name": "urgent"}).data
    b = api.post("/api/tags/", {"name": "important"}).data
    child = api.post("/api/tags/", {"name": "sous", "parent": a["id"]}).data
    task = api.post(
        "/api/tasks/", {"project": inbox.id, "title": "T", "tags": [a["id"]]}
    ).data
    api.post(f"/api/tags/{a['id']}/merge/", {"target": b["id"]})
    assert api.get(f"/api/tags/{a['id']}/").status_code == 404
    assert api.get(f"/api/tasks/{task['id']}/").data["tags"] == [b["id"]]
    assert api.get(f"/api/tags/{child['id']}/").data["parent"] == b["id"]


def test_duplicate_tag_name_rejected(api):
    api.post("/api/tags/", {"name": "x"})
    assert api.post("/api/tags/", {"name": "x"}).status_code == 400
