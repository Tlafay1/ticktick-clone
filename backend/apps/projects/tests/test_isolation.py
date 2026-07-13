"""Isolation en écriture : une FK ne doit jamais pointer chez autrui.

get_queryset protège la lecture ; ces tests couvrent la création/màj, où une
FK (project, group, section) fournie par le client pourrait cibler un autre
utilisateur si le serializer ne la valide pas.
"""
import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def other(django_user_model):
    return django_user_model.objects.create_user(email="o@x.com", password="x")


def test_section_cannot_target_other_users_project(api, other):
    other_project = other.projects.get(is_inbox=True)
    resp = api.post("/api/sections/", {"project": other_project.id, "name": "Intrus"})
    assert resp.status_code == 400
    assert "sections" not in [s.name for s in other_project.sections.all()]


def test_project_group_cannot_target_other_users_folder(api, other):
    from apps.projects.models import ProjectGroup

    foreign_group = ProjectGroup.objects.create(user=other, name="Dossier autrui")
    resp = api.post("/api/projects/", {"name": "Ma liste", "group": foreign_group.id})
    assert resp.status_code == 400


def test_task_cannot_reference_other_users_section(api, inbox, other):
    from apps.projects.models import Section

    other_project = other.projects.get(is_inbox=True)
    foreign_section = Section.objects.create(project=other_project, name="Colonne autrui")
    resp = api.post(
        "/api/tasks/",
        {"project": inbox.id, "title": "T", "section": foreign_section.id},
        format="json",
    )
    assert resp.status_code == 400


def test_task_section_must_belong_to_its_project(api, inbox):
    """Section et liste appartiennent au user, mais ne correspondent pas."""
    project = api.post("/api/projects/", {"name": "Autre liste"}).data
    section = api.post("/api/sections/", {"project": project["id"], "name": "S"}).data
    resp = api.post(
        "/api/tasks/",
        {"project": inbox.id, "title": "T", "section": section["id"]},
        format="json",
    )
    assert resp.status_code == 400
