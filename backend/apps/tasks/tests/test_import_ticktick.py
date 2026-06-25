"""Tests de l'importeur du format d'export CSV officiel de TickTick."""

import pytest

from apps.projects.models import Project, ProjectGroup, Section
from apps.tags.models import Tag
from apps.tasks.models import Task
from apps.tasks.ticktick_import import import_ticktick_csv, looks_like_ticktick_csv

HEADER = (
    '"Folder Name","List Name","Title","Kind","Tags","Content","Is Check list",'
    '"Start Date","Due Date","Reminder","Repeat","Priority","Status","Created Time",'
    '"Completed Time","Order","Timezone","Is All Day","Is Floating","Column Name",'
    '"Column Order","View Mode","taskId","parentId","projectKind"'
)

# 6 lignes de méta (dont la légende de statut multi-lignes) comme dans l'export réel.
META = (
    '"Date: 2026-06-15+0000"\n'
    '"Version: 7.2"\n'
    '"Status: \n0 Normal\n1 Completed\n2 Archived"\n'
)


def _csv(*rows):
    return META + HEADER + "\n" + "\n".join(rows) + "\n"


def _row(folder="", lst="", title="", tags="", content="", start="", due="",
         reminder="", repeat="", priority="0", status="0", created="", completed="",
         order="0", tz="", all_day="false", column="", view="list",
         task_id="", parent_id="", kind="TASK"):
    cells = [folder, lst, title, "TEXT", tags, content, "N", start, due, reminder,
             repeat, priority, status, created, completed, order, tz, all_day,
             "false", column, "", view, task_id, parent_id, kind]
    return ",".join(f'"{c}"' for c in cells)


def test_detection(user):
    assert looks_like_ticktick_csv(_csv())
    assert not looks_like_ticktick_csv("title,description\nfoo,bar")


@pytest.mark.django_db
def test_import_structure_complete(user, inbox):
    csv_content = _csv(
        _row(folder="Travail", lst="Projets", title="Tâche parent", tags="urgent,perso",
             content="notes", due="2026-06-20T09:00:00+0000", repeat="RRULE:FREQ=WEEKLY",
             priority="5", order="100", view="kanban", column="En cours", task_id="p1"),
        _row(folder="Travail", lst="Projets", title="Sous-tâche", priority="3",
             view="kanban", task_id="c1", parent_id="p1"),
        _row(lst="Courses", title="Lait", status="2",
             created="2026-06-01T10:00:00+0000", completed="2026-06-02T12:00:00+0000"),
        _row(lst="Notes", title="une note", kind="NOTE", task_id="n1"),
    )

    stats = import_ticktick_csv(user, csv_content)

    assert stats["imported"] == 3            # la NOTE est ignorée
    assert stats["skipped"] == 1
    assert stats["folders_created"] == 1
    assert stats["projects_created"] == 2    # Projets + Courses (Inbox déjà là)
    assert stats["tags_created"] == 2

    # Dossier + liste kanban rattachés.
    group = ProjectGroup.objects.get(user=user, name="Travail")
    projets = Project.objects.get(user=user, name="Projets")
    assert projets.group == group
    assert projets.view_mode == Project.ViewMode.KANBAN

    # Tâche parent : tags, récurrence (préfixe RRULE: retiré), priorité, section kanban.
    parent = Task.objects.get(title="Tâche parent")
    assert parent.priority == 5
    assert parent.rrule == "FREQ=WEEKLY"
    assert set(parent.tags.values_list("name", flat=True)) == {"urgent", "perso"}
    assert parent.section == Section.objects.get(project=projets, name="En cours")
    assert parent.due_date is not None

    # Hiérarchie de sous-tâche reconstruite via taskId/parentId.
    child = Task.objects.get(title="Sous-tâche")
    assert child.parent == parent

    # Tâche terminée : statut + date d'achèvement + date de création préservée.
    lait = Task.objects.get(title="Lait")
    assert lait.status == Task.Status.COMPLETED
    assert lait.completed_at is not None
    assert lait.created_at.isoformat().startswith("2026-06-01")


@pytest.mark.django_db
def test_import_dedupe(user, inbox):
    row = _row(lst="Courses", title="Lait")
    import_ticktick_csv(user, _csv(row))
    stats = import_ticktick_csv(user, _csv(row), dedupe=True)
    assert stats["imported"] == 0
    assert stats["skipped"] == 1
    assert Task.objects.filter(user=user, title="Lait").count() == 1


@pytest.mark.django_db
def test_import_upsert_by_task_id(user, inbox):
    """Réimporter le même CSV met à jour les tâches (pas de doublon) grâce au taskId."""
    row_v1 = _row(lst="Courses", title="Lait", priority="1", task_id="abc123")
    stats1 = import_ticktick_csv(user, _csv(row_v1))
    assert stats1["imported"] == 1
    assert stats1["updated"] == 0

    row_v2 = _row(lst="Courses", title="Lait mis à jour", priority="5", task_id="abc123")
    stats2 = import_ticktick_csv(user, _csv(row_v2))
    assert stats2["imported"] == 0
    assert stats2["updated"] == 1
    assert Task.objects.filter(user=user).count() == 1
    task = Task.objects.get(user=user, external_id="abc123")
    assert task.title == "Lait mis à jour"
    assert task.priority == 5
