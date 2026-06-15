"""Client de référence pour piloter le clone TickTick depuis un agent IA.

But : remplacer `TickTickManager.get_client()` dans le repo de l'agent **sans
toucher aux fichiers d'outils Gemini** (`ticktick_create_task`, etc.). Les méthodes
exposées ici portent les mêmes noms/signatures que celles attendues par ces outils,
et renvoient des modèles `ticktick_sdk` (`Task`, `Project`, …) pour rester
compatibles avec le code existant.

Installation côté agent :
    pip install httpx
    # copier ce fichier dans le projet de l'agent, puis :
    #   client = CloneClient(base_url="https://tasks.exemple.com", api_key="<clé>")
    # et faire en sorte que TickTickManager.get_client() le retourne.

Authentification : clé d'API longue durée (header `Api-Key`), générée via
`POST /api/api-keys/` ou l'admin Django. Pas de refresh JWT à gérer.

NOTE de mapping : le clone expose des champs en snake_case (`due_date`, `description`,
`rrule`, `section`, `is_pinned`). On les traduit vers les noms attendus par
`ticktick_sdk` (`desc`, `repeat_flag`, `is_all_day`, `reminders`, `project_id`,
`column_id`). Si votre version du SDK diffère, ajuster `_to_task` / `_to_project`.
"""

from __future__ import annotations

import re
import shlex
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

# Modèles du SDK utilisé par les outils de l'agent (mêmes imports que les outils).
from ticktick_sdk import Column, Habit, Project, ProjectGroup, Tag, Task
from ticktick_sdk.models.task import TaskReminder

# --------------------------------------------------------------------------- #
# Conversion clone (JSON REST) -> modèles ticktick_sdk
# --------------------------------------------------------------------------- #

_STATUS_COMPLETED = 2


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _to_task(d: dict) -> Task:
    """Mappe une tâche du clone vers un `Task` du SDK."""
    return Task(
        id=str(d["id"]),
        project_id=str(d.get("project")) if d.get("project") else None,
        parent_id=str(d["parent"]) if d.get("parent") else None,
        title=d.get("title", ""),
        content=d.get("description", ""),
        desc=d.get("description", ""),
        priority=d.get("priority", 0),
        status=d.get("status", 0),
        start_date=_parse_dt(d.get("start_date")),
        due_date=_parse_dt(d.get("due_date")),
        completed_time=_parse_dt(d.get("completed_at")),
        created_time=_parse_dt(d.get("created_at")),
        modified_time=_parse_dt(d.get("modified_at")),
        is_all_day=d.get("is_all_day", True),
        repeat_flag=d.get("rrule", "") or "",
        column_id=str(d["section"]) if d.get("section") else None,
        tags=[t["name"] if isinstance(t, dict) else t for t in d.get("tags", [])],
        reminders=[
            TaskReminder(id=str(r.get("id", "")), trigger=_reminder_trigger(r))
            for r in d.get("reminders", [])
        ],
    )


def _reminder_trigger(r: dict) -> str:
    """Reconstitue un TRIGGER ISO8601 à partir d'un rappel relatif du clone."""
    minutes = r.get("minutes_before")
    if minutes is not None:
        return f"TRIGGER:-PT{minutes}M"
    return "TRIGGER:PT0S"


_TRIGGER_RE = re.compile(r"(?:-)?\s*P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?")


def _trigger_to_reminder(trigger: Any) -> dict:
    """Convertit un TRIGGER TickTick (chaîne ou dict) en payload de rappel du clone."""
    if isinstance(trigger, dict):
        return trigger  # déjà au bon format
    s = str(trigger)
    m = _TRIGGER_RE.search(s)
    if not m:
        return {"trigger_type": "RELATIVE", "minutes_before": 0}
    days    = int(m.group(1) or 0)
    hours   = int(m.group(2) or 0)
    minutes = int(m.group(3) or 0)
    return {"trigger_type": "RELATIVE", "minutes_before": days * 1440 + hours * 60 + minutes}


def _from_task_kwargs(**kwargs) -> dict:
    """Traduit les kwargs des outils (noms TickTick) vers le payload du clone.

    Les valeurs `None` sont omises (PATCH partiel). Pour effacer un champ,
    passer la clé avec la valeur `None` et appeler directement `_patch` avec
    `{"field": null}`, ou utiliser `_CLEAR` comme valeur.
    """
    mapping = {
        "content": "description",
        "description": "description",
        "all_day": "is_all_day",
        "recurrence": "rrule",
        "parent_id": "parent",
        "project_id": "project",
        "column_id": "section",
    }
    payload: dict[str, Any] = {}
    for key, value in kwargs.items():
        if value is None:
            continue
        payload[mapping.get(key, key)] = value
    return payload


def _to_project(d: dict) -> Project:
    return Project(
        id=str(d["id"]),
        name=d.get("name", ""),
        color=d.get("color", ""),
        view_mode=d.get("view_mode", "list"),
        folder_id=str(d["group"]) if d.get("group") else None,
        kind="TASK",
    )


def _to_folder(d: dict) -> ProjectGroup:
    return ProjectGroup(id=str(d["id"]), name=d.get("name", ""))


def _to_tag(d: dict) -> Tag:
    return Tag(name=d.get("name", ""), color=d.get("color", ""),
               parent=d.get("parent"))


def _to_column(d: dict) -> Column:
    return Column(id=str(d["id"]), project_id=str(d.get("project")),
                  name=d.get("name", ""), sort_order=d.get("sort_order", 0))


def _to_habit(d: dict) -> Habit:
    return Habit(id=str(d["id"]), name=d.get("name", ""), **{
        k: d[k] for k in ("goal", "step", "unit", "color") if k in d
    })


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #


class CloneClient:
    """Adaptateur REST : même surface que le client TickTick d'origine."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 15.0):
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/api",
            headers={"Authorization": f"Api-Key {api_key}"},
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get(self, path: str, **params) -> Any:
        r = await self._http.get(path, params={k: v for k, v in params.items() if v is not None})
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, json: dict) -> Any:
        r = await self._http.post(path, json=json)
        r.raise_for_status()
        return r.json()

    async def _patch(self, path: str, json: dict) -> Any:
        r = await self._http.patch(path, json=json)
        r.raise_for_status()
        return r.json()

    # ----- Tâches -----

    async def get_all_tasks(self) -> list[Task]:
        return [_to_task(t) for t in await self._get("/tasks/")]

    async def get_today_tasks(self) -> list[Task]:
        end = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        data = await self._get("/tasks/", smart=1, due_before=end.isoformat(), status=0)
        return [_to_task(t) for t in data]

    async def get_overdue_tasks(self) -> list[Task]:
        now = datetime.now(timezone.utc).isoformat()
        data = await self._get("/tasks/", smart=1, due_before=now, status=0)
        return [_to_task(t) for t in data]

    async def get_task(self, task_id: str, project_id: Optional[str] = None) -> Task:
        return _to_task(await self._get(f"/tasks/{task_id}/"))

    async def create_task(self, **kwargs) -> Task:
        payload = _from_task_kwargs(**kwargs)
        # Tags : noms → IDs (le backend attend des IDs)
        if "tags" in payload and payload["tags"]:
            payload["tags"] = await self._resolve_tag_ids(
                [t if isinstance(t, str) else t for t in payload["tags"]]
            )
        # Rappels : convertit TRIGGER:-PT30M → {minutes_before: 30}
        if "reminders" in payload:
            payload["reminders"] = [_trigger_to_reminder(r) for r in payload["reminders"] if r]
        return _to_task(await self._post("/tasks/", payload))

    async def update_task(self, task: Task) -> Task:
        due = getattr(task, "due_date", None)
        start = getattr(task, "start_date", None)
        payload = _from_task_kwargs(
            title=task.title,
            description=getattr(task, "desc", None),
            priority=task.priority,
            status=task.status,
            recurrence=getattr(task, "repeat_flag", None),
            all_day=getattr(task, "is_all_day", None),
            due_date=due.isoformat() if due else None,
            start_date=start.isoformat() if start else None,
            project_id=getattr(task, "project_id", None),
            column_id=getattr(task, "column_id", None),
        )
        tag_names = getattr(task, "tags", None)
        if tag_names is not None:
            payload["tags"] = await self._resolve_tag_ids(tag_names)
        reminders = getattr(task, "reminders", None)
        if reminders is not None:
            payload["reminders"] = [
                _trigger_to_reminder(r.trigger if hasattr(r, "trigger") else r)
                for r in reminders
            ]
        return _to_task(await self._patch(f"/tasks/{task.id}/", payload))

    async def complete_task(self, task_id: str, project_id: Optional[str] = None) -> Task:
        return _to_task(await self._patch(f"/tasks/{task_id}/", {"status": _STATUS_COMPLETED}))

    async def delete_task(self, task_id: str, project_id: Optional[str] = None) -> None:
        r = await self._http.delete(f"/tasks/{task_id}/")
        r.raise_for_status()

    async def move_task(self, task_id: str, from_project_id: str, to_project_id: str) -> Task:
        return _to_task(await self._patch(f"/tasks/{task_id}/", {"project": to_project_id}))

    async def search_tasks(self, query: str) -> list[Task]:
        """Recherche avec syntaxe filtre optionnelle.

        Tokens reconnus (insensibles à la casse) :
          status:open|done|wontdo        priority:high|medium|low|none
          due:today|overdue|thisweek     project:<nom>   tag:<nom>   #<nom>
          is_pinned:true                 has_date:true
        Le reste du texte est passé comme recherche plein-texte (?q=).

        Exemples :
          "status:open due:today"          → tâches non terminées dues aujourd'hui
          "priority:high #travail"         → haute priorité, tag "travail"
          "projet:Dev réunion"             → projet "Dev", titre contient "réunion"
          "*" ou ""                        → toutes les tâches actives
        """
        params = await self._build_filter_params(query)
        return [_to_task(t) for t in await self._get("/tasks/", **params)]

    async def _build_filter_params(self, query: str) -> dict[str, Any]:
        """Traduit une requête textuelle en params d'API via shlex."""
        query = (query or "").strip()
        if not query or query == "*":
            return {}

        try:
            tokens = shlex.split(query)
        except ValueError:
            tokens = query.split()

        now = datetime.now(timezone.utc)
        params: dict[str, Any] = {}
        text_parts: list[str] = []

        _status_map = {"open": 0, "normal": 0, "active": 0,
                       "done": 2, "completed": 2, "wontdo": -1, "wont_do": -1}
        _prio_map   = {"high": 5, "medium": 3, "low": 1, "none": 0}

        for token in tokens:
            if token.startswith("#"):
                params["tag"] = token[1:]
                continue
            if ":" not in token:
                text_parts.append(token)
                continue

            key, _, val = token.partition(":")
            key = key.lower()
            val_lower = val.lower()

            if key in ("status", "état"):
                params["status"] = _status_map.get(val_lower, 0)

            elif key in ("priority", "priorité", "prio"):
                params["priority"] = _prio_map.get(val_lower, 0)

            elif key == "due":
                if val_lower == "today":
                    tomorrow = (now + timedelta(days=1)).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    params.setdefault("due_before", tomorrow.isoformat())
                    params.setdefault("has_date", "true")
                elif val_lower in ("overdue", "past", "late"):
                    params.setdefault("due_before", now.isoformat())
                    params.setdefault("status", 0)
                elif val_lower in ("thisweek", "this_week", "week"):
                    end = (now + timedelta(days=7)).replace(
                        hour=23, minute=59, second=59, microsecond=0
                    )
                    params.setdefault("due_before", end.isoformat())
                    params.setdefault("has_date", "true")
                else:
                    # date ISO directe
                    params["due_before"] = val

            elif key in ("tag", "label", "étiquette"):
                params["tag"] = val

            elif key in ("project", "list", "liste", "projet"):
                # Résolution par nom → id (avec cache)
                pid = await self._resolve_project_name(val)
                if pid:
                    params["project"] = pid

            elif key in ("is_pinned", "pinned", "épinglé"):
                params["is_pinned"] = val_lower in ("true", "1", "yes", "oui")

            elif key in ("has_date", "scheduled"):
                params["has_date"] = val_lower in ("true", "1", "yes", "oui")

            elif key == "section":
                params["section"] = val

            else:
                # clé inconnue → repasse en texte libre
                text_parts.append(token)

        if text_parts:
            params["q"] = " ".join(text_parts)

        return params

    def _invalidate_caches(self) -> None:
        self.__dict__.pop("_project_cache", None)
        self.__dict__.pop("_tag_cache", None)

    async def _resolve_project_name(self, name: str) -> Optional[int]:
        """Retourne l'id du premier projet dont le nom correspond (insensible à la casse)."""
        if not hasattr(self, "_project_cache"):
            self._project_cache: list[dict] = await self._get("/projects/")
        name_lower = name.lower()
        match = next(
            (p for p in self._project_cache if p.get("name", "").lower() == name_lower),
            None,
        )
        return match["id"] if match else None

    async def _resolve_tag_ids(self, names: list[str]) -> list[int]:
        """Convertit une liste de noms de tags en IDs (crée les tags manquants)."""
        if not hasattr(self, "_tag_cache"):
            self._tag_cache: list[dict] = await self._get("/tags/")
        result = []
        for name in names:
            name_lower = name.lower()
            match = next((t for t in self._tag_cache if t.get("name", "").lower() == name_lower), None)
            if not match:
                match = await self._post("/tags/", {"name": name})
                self._tag_cache.append(match)
            result.append(match["id"])
        return result

    async def pin_task(self, task_id: str, project_id: Optional[str] = None) -> Task:
        return _to_task(await self._patch(f"/tasks/{task_id}/", {"is_pinned": True}))

    async def unpin_task(self, task_id: str, project_id: Optional[str] = None) -> Task:
        return _to_task(await self._patch(f"/tasks/{task_id}/", {"is_pinned": False}))

    async def move_task_to_column(self, task_id: str, project_id: str,
                                  column_id: Optional[str] = None) -> Task:
        return _to_task(await self._patch(f"/tasks/{task_id}/", {"section": column_id}))

    # ----- Projets / dossiers -----

    async def get_all_projects(self) -> list[Project]:
        return [_to_project(p) for p in await self._get("/projects/")]

    async def create_project(self, name: str, color: Optional[str] = None,
                             kind: str = "TASK", view_mode: str = "list",
                             folder_id: Optional[str] = None) -> Project:
        payload = {"name": name, "view_mode": view_mode}
        if color:
            payload["color"] = color
        if folder_id:
            payload["group"] = folder_id
        result = _to_project(await self._post("/projects/", payload))
        self._invalidate_caches()
        return result

    async def update_project(self, project_id: str, name: Optional[str] = None,
                             color: Optional[str] = None,
                             folder_id: Optional[str] = None) -> Project:
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if color is not None:
            payload["color"] = color
        if folder_id is not None:
            payload["group"] = None if folder_id == "NONE" else folder_id
        return _to_project(await self._patch(f"/projects/{project_id}/", payload))

    async def delete_project(self, project_id: str) -> None:
        r = await self._http.delete(f"/projects/{project_id}/")
        r.raise_for_status()

    async def get_all_folders(self) -> list[ProjectGroup]:
        return [_to_folder(g) for g in await self._get("/project-groups/")]

    async def create_folder(self, name: str) -> ProjectGroup:
        return _to_folder(await self._post("/project-groups/", {"name": name}))

    async def update_folder(self, folder_id: str, name: str) -> ProjectGroup:
        return _to_folder(await self._patch(f"/project-groups/{folder_id}/", {"name": name}))

    async def delete_folder(self, folder_id: str) -> None:
        r = await self._http.delete(f"/project-groups/{folder_id}/")
        r.raise_for_status()

    # ----- Colonnes kanban (= sections) -----

    async def get_columns(self, project_id: str) -> list[Column]:
        return [_to_column(s) for s in await self._get("/sections/", project=project_id)]

    async def create_column(self, project_id: str, name: str,
                            sort_order: Optional[int] = None) -> Column:
        payload = {"project": project_id, "name": name}
        if sort_order is not None:
            payload["sort_order"] = sort_order
        return _to_column(await self._post("/sections/", payload))

    # ----- Tags -----

    async def get_all_tags(self) -> list[Tag]:
        return [_to_tag(t) for t in await self._get("/tags/")]

    async def create_tag(self, name: str, color: Optional[str] = None,
                         parent: Optional[str] = None) -> Tag:
        payload = {"name": name}
        if color:
            payload["color"] = color
        if parent:
            payload["parent"] = parent
        return _to_tag(await self._post("/tags/", payload))

    async def delete_tag(self, name: str) -> None:
        tags = await self._get("/tags/")
        match = next((t for t in tags if t.get("name") == name), None)
        if match:
            r = await self._http.delete(f"/tags/{match['id']}/")
            r.raise_for_status()

    # ----- Habitudes -----

    async def get_all_habits(self) -> list[Habit]:
        return [_to_habit(h) for h in await self._get("/habits/")]

    async def create_habit(self, **kwargs) -> Habit:
        return _to_habit(await self._post("/habits/", kwargs))

    async def update_habit(self, habit_id: str, **kwargs) -> Habit:
        return _to_habit(await self._patch(f"/habits/{habit_id}/", kwargs))

    async def delete_habit(self, habit_id: str) -> None:
        r = await self._http.delete(f"/habits/{habit_id}/")
        r.raise_for_status()

    async def checkin_habit(self, habit_id: str, value: float = 1.0) -> Habit:
        await self._post(f"/habits/{habit_id}/checkins/", {"value": value})
        return _to_habit(await self._get(f"/habits/{habit_id}/"))

    # ----- Focus -----

    async def get_focus_by_tag(self, days: int = 7) -> dict:
        data = await self._get("/focus-sessions/stats/", days=days)
        return data.get("by_tag", {})
