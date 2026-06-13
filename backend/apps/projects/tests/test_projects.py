import pytest

pytestmark = pytest.mark.django_db


def test_inbox_cannot_be_deleted_or_renamed(api, inbox):
    assert api.delete(f"/api/projects/{inbox.id}/").status_code == 400
    assert api.patch(f"/api/projects/{inbox.id}/", {"name": "X"}).status_code == 400
    # Mais ses autres réglages restent modifiables.
    assert api.patch(f"/api/projects/{inbox.id}/", {"color": "#ff0000"}).status_code == 200


def test_project_crud_with_group_and_sections(api):
    group = api.post("/api/project-groups/", {"name": "Travail"}).data
    project = api.post(
        "/api/projects/",
        {"name": "Client A", "color": "#3b82f6", "icon": "💼", "group": group["id"]},
    ).data
    assert project["view_mode"] == "list"
    section = api.post(
        "/api/sections/", {"project": project["id"], "name": "En cours"}
    ).data
    detail = api.get(f"/api/projects/{project['id']}/").data
    assert detail["sections"][0]["id"] == section["id"]


def test_user_isolation(api, user, django_user_model):
    other = django_user_model.objects.create_user(email="o@x.com", password="x")
    other_inbox = other.projects.get(is_inbox=True)
    assert api.get(f"/api/projects/{other_inbox.id}/").status_code == 404
