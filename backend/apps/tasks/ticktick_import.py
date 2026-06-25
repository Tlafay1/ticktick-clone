"""Importeur du format d'export CSV officiel de TickTick.

L'export TickTick comporte ~6 lignes de méta en tête (Date, Version, légende des
statuts sur plusieurs lignes) puis une ligne d'en-tête de colonnes et les tâches.
On localise l'en-tête (`"Folder Name"`) puis on reconstruit dossiers, listes,
sections kanban, tags, dates, récurrence, rappels et hiérarchie de sous-tâches.
"""

import csv
import io
import re
from datetime import timezone as dt_timezone

from dateutil import parser as date_parser

from apps.projects.models import Project, ProjectGroup, Section
from apps.tags.models import Tag

from .models import MAX_SUBTASK_DEPTH, Reminder, Task

HEADER_MARKER = "Folder Name"
ALLOWED_PRIORITIES = {0, 1, 3, 5}


def looks_like_ticktick_csv(content):
    """Vrai si le contenu ressemble à un export TickTick (en-tête reconnu)."""
    return HEADER_MARKER in content and "List Name" in content


def _parse_dt(value):
    """Parse une date TickTick (ISO + offset) en datetime aware UTC, ou None."""
    if not value:
        return None
    try:
        dt = date_parser.parse(value)
    except (ValueError, OverflowError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc)


def _parse_bool(value):
    return str(value).strip().lower() == "true"


_DURATION_RE = re.compile(
    r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?"
)


def _trigger_to_minutes(trigger):
    """Convertit un TRIGGER:-PT30M / -P1DT0M TickTick en minutes avant échéance."""
    m = _DURATION_RE.search(trigger or "")
    if not m:
        return None
    parts = {k: int(v) for k, v in m.groupdict(default=0).items()}
    return parts["days"] * 1440 + parts["hours"] * 60 + parts["minutes"]


def _split_header(content):
    """Retourne les lignes CSV à partir de l'en-tête de colonnes (méta ignorée)."""
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith('"' + HEADER_MARKER) or line.lstrip().startswith(HEADER_MARKER):
            return "\n".join(lines[i:])
    return content


def import_ticktick_csv(user, content, dedupe=False):
    """Importe (ou met à jour) un export TickTick pour `user`. Retourne un récap chiffré."""
    reader = csv.DictReader(io.StringIO(_split_header(content)))

    folders = {}   # nom -> ProjectGroup
    projects = {}  # (nom_liste) -> Project
    sections = {}  # (project_id, nom_colonne) -> Section
    tags_cache = {}  # nom -> Tag
    id_map = {}    # taskId TickTick -> Task créé/mis à jour
    parent_links = []  # (taskId, parentId)
    stats = {"imported": 0, "updated": 0, "folders_created": 0, "projects_created": 0,
             "tags_created": 0, "skipped": 0}

    inbox = Project.objects.filter(user=user, is_inbox=True).first()

    def get_folder(name):
        name = (name or "").strip()
        if not name:
            return None
        if name not in folders:
            obj, created = ProjectGroup.objects.get_or_create(user=user, name=name)
            folders[name] = obj
            stats["folders_created"] += int(created)
        return folders[name]

    def get_project(list_name, folder, view_mode):
        list_name = (list_name or "").strip()
        if not list_name:
            return inbox
        if list_name not in projects:
            obj, created = Project.objects.get_or_create(
                user=user, name=list_name,
                defaults={"group": folder, "view_mode": view_mode or Project.ViewMode.LIST},
            )
            projects[list_name] = obj
            stats["projects_created"] += int(created)
        return projects[list_name]

    def get_section(project, column_name):
        column_name = (column_name or "").strip()
        if not column_name:
            return None
        key = (project.id, column_name)
        if key not in sections:
            sections[key], _ = Section.objects.get_or_create(
                project=project, name=column_name
            )
        return sections[key]

    def get_tag(name):
        name = name.strip()
        if not name:
            return None
        if name not in tags_cache:
            obj, created = Tag.objects.get_or_create(user=user, name=name)
            tags_cache[name] = obj
            stats["tags_created"] += int(created)
        return tags_cache[name]

    for row in reader:
        if (row.get("projectKind") or "").strip().upper() == "NOTE":
            stats["skipped"] += 1
            continue
        title = (row.get("Title") or "").strip()
        if not title:
            stats["skipped"] += 1
            continue

        folder = get_folder(row.get("Folder Name"))
        view_mode = (row.get("View Mode") or "").strip() or Project.ViewMode.LIST
        if view_mode not in Project.ViewMode.values:
            view_mode = Project.ViewMode.LIST
        project = get_project(row.get("List Name"), folder, view_mode)

        completed_at = _parse_dt(row.get("Completed Time"))
        raw_status = (row.get("Status") or "").strip()
        if completed_at:
            task_status = Task.Status.COMPLETED
        elif raw_status == "-1":
            task_status = Task.Status.WONT_DO
        else:
            task_status = Task.Status.NORMAL

        try:
            priority = int(row.get("Priority") or 0)
        except ValueError:
            priority = 0
        if priority not in ALLOWED_PRIORITIES:
            priority = 0

        try:
            sort_order = int(row.get("Order") or 0)
        except ValueError:
            sort_order = 0

        repeat = (row.get("Repeat") or "").strip()
        rrule = repeat[6:] if repeat.upper().startswith("RRULE:") else repeat

        task_id = (row.get("taskId") or "").strip()
        parent_id = (row.get("parentId") or "").strip()

        task_fields = dict(
            project=project,
            section=get_section(project, row.get("Column Name")),
            title=title,
            description=row.get("Content") or "",
            status=task_status,
            priority=priority,
            sort_order=sort_order,
            start_date=_parse_dt(row.get("Start Date")),
            due_date=_parse_dt(row.get("Due Date")),
            is_all_day=_parse_bool(row.get("Is All Day")),
            timezone_name=(row.get("Timezone") or "").strip(),
            rrule=rrule,
            completed_at=completed_at,
            parent=None,  # réassigné en 2e passe
        )

        if task_id:
            # Upsert par identifiant TickTick — idempotent.
            task, created = Task.objects.update_or_create(
                user=user, external_id=task_id,
                defaults=task_fields,
            )
        elif dedupe and Task.objects.filter(user=user, project=project, title=title).exists():
            stats["skipped"] += 1
            continue
        else:
            task = Task.objects.create(user=user, external_id="", **task_fields)
            created = True

        if not created:
            # Réinitialiser rappels avant de les ré-importer.
            task.reminders.all().delete()

        tag_names = [t for t in re.split(r",", row.get("Tags") or "") if t.strip()]
        tag_objs = [get_tag(t) for t in tag_names]
        tag_objs = [t for t in tag_objs if t]
        task.tags.set(tag_objs)

        # Rappels (max 5) — déclencheurs relatifs déduits du champ Reminder.
        triggers = [t for t in re.split(r",", row.get("Reminder") or "") if "TRIGGER" in t.upper()]
        for trig in triggers[:5]:
            minutes = _trigger_to_minutes(trig)
            if minutes is not None:
                Reminder.objects.create(
                    task=task, trigger_type=Reminder.TriggerType.RELATIVE,
                    minutes_before=minutes,
                )

        # Préserver la date de création (auto_now_add → contournée via update()).
        created_at = _parse_dt(row.get("Created Time"))
        if created_at:
            Task.objects.filter(pk=task.pk).update(created_at=created_at)

        if task_id:
            id_map[task_id] = task
        if task_id and parent_id:
            parent_links.append((task_id, parent_id))
        stats["imported" if created else "updated"] += 1

    # 2e passe : relier les sous-tâches (respect de la profondeur max).
    for task_id, parent_id in parent_links:
        child = id_map.get(task_id)
        parent = id_map.get(parent_id)
        if child and parent and parent.depth < MAX_SUBTASK_DEPTH:
            child.parent = parent
            child.save(update_fields=["parent"])

    return stats
