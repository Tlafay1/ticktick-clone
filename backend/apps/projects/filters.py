"""Moteur des smart lists custom : applique `Project.filter_rules` (module 2.3).

Format des règles = celui produit par l'éditeur web (FilterEditor.vue,
`FilterRule` dans web/src/types.ts) :

    [{"type": "and" | "or", "rules": [<règle>...]}, ...]

où une règle est soit un groupe imbriqué (même forme), soit une feuille
``{"field", "op", "value"}`` :

- ``field`` ∈ ``priority`` | ``status`` | ``due`` | ``tag`` | ``project``
  (alias ``list`` accepté) ;
- ``op`` ∈ ``eq`` | ``neq`` | ``lt`` | ``gt`` | ``in`` | ``not_in`` | ``all``
  | ``is_null`` | ``is_not_null`` ;
- ``due`` accepte les valeurs relatives ``today`` / ``tomorrow`` / ``week``
  (7 jours glissants, même sémantique que la smart list Next 7 Days) /
  ``overdue``, ou une date/datetime ISO absolue ;
- ``tag`` accepte un id numérique ou un nom, ou une liste des deux ;
- ``project`` accepte un id ou une liste d'ids.

La liste racine est un AND implicite ; un groupe vide est neutre (ignoré) ;
une feuille inconnue ou incohérente ne matche RIEN (plutôt que de tout
laisser passer silencieusement).

Politique des listes masquées (module 25.2) : les tâches d'une liste
``hidden_from_smart_lists`` ou archivée sont exclues, sauf si la liste est
explicitement ciblée en inclusion (``project`` avec ``eq``/``in``).

NB : les conditions sur ``tags`` (M2M) passent par des sous-requêtes
``pk__in`` — combiner deux ``Q(tags__…)`` dans un même filter() exigerait
la même ligne de jointure et ne matcherait jamais (cas « contient tous »).
"""
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime


def _impossible():
    return Q(pk__in=[])


def apply_smart_list(qs, project):
    """Filtre `qs` (tâches déjà scoppées utilisateur) selon la smart list."""
    rules = project.filter_rules or []
    now = timezone.now()
    qs = qs.filter(_group_q({"type": "and", "rules": rules}, now))

    # Listes masquées / archivées : exclues sauf inclusion explicite.
    included = set()
    _collect_included_projects(rules, included)
    visible = Q(project__hidden_from_smart_lists=False, project__archived=False)
    if included:
        visible |= Q(project_id__in=included)
    return qs.filter(visible)


def _group_q(group, now):
    parts = [_rule_q(r, now) for r in group.get("rules", []) if isinstance(r, dict)]
    if not parts:
        return Q()  # groupe vide : neutre
    combined = parts[0]
    is_or = str(group.get("type", "and")).lower() == "or"
    for q in parts[1:]:
        combined = (combined | q) if is_or else (combined & q)
    return combined


def _rule_q(rule, now):
    if "rules" in rule:  # groupe imbriqué
        return _group_q(rule, now)
    field = rule.get("field")
    if field == "list":
        field = "project"
    op = rule.get("op", rule.get("operator"))
    handler = _HANDLERS.get(field)
    q = handler(op, rule.get("value"), now) if handler else None
    return q if q is not None else _impossible()


def _as_list(value):
    return value if isinstance(value, list) else [value]


# ----- Feuilles par champ ----------------------------------------------------

def _priority_q(op, value, now):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    return {
        "eq": Q(priority=v),
        "neq": ~Q(priority=v),
        "lt": Q(priority__lt=v),
        "gt": Q(priority__gt=v),
    }.get(op)


def _status_q(op, value, now):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    return {"eq": Q(status=v), "neq": ~Q(status=v)}.get(op)


def _due_window(value, now):
    """Résout une valeur d'échéance en fenêtre (start, end) — end exclusif."""
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if value == "today":
        return day, day + timedelta(days=1)
    if value == "tomorrow":
        return day + timedelta(days=1), day + timedelta(days=2)
    if value == "week":
        return day, day + timedelta(days=7)
    if value == "overdue":
        return None, now
    if isinstance(value, str):
        dt = parse_datetime(value)
        if dt is not None:
            if timezone.is_naive(dt):
                dt = dt.replace(tzinfo=dt_timezone.utc)
            return dt, dt + timedelta(days=1)
        d = parse_date(value)
        if d is not None:
            start = datetime(d.year, d.month, d.day, tzinfo=dt_timezone.utc)
            return start, start + timedelta(days=1)
    return None


def _due_q(op, value, now):
    if op == "is_null":
        return Q(due_date__isnull=True)
    if op == "is_not_null":
        return Q(due_date__isnull=False)
    window = _due_window(value, now)
    if window is None:
        return None
    start, end = window
    if op == "eq":
        q = Q()
        if start is not None:
            q &= Q(due_date__gte=start)
        if end is not None:
            q &= Q(due_date__lt=end)
        return q
    if op == "lt":
        limit = start if start is not None else end
        return Q(due_date__lt=limit)
    if op == "gt":
        return Q(due_date__gte=end) if end is not None else None
    return None


def _has_tag_q(value):
    """Sous-requête « possède le tag <id ou nom> » (composable en AND/OR/NOT)."""
    from apps.tasks.models import Task

    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        cond = {"tags__id": int(value)}
    elif isinstance(value, str) and value:
        cond = {"tags__name": value}
    else:
        return None
    return Q(pk__in=Task.objects.filter(**cond).values("pk"))


def _tags_q(op, value, now):
    from apps.tasks.models import Task

    if op == "is_null":
        return Q(tags__isnull=True)
    if op == "is_not_null":
        return Q(pk__in=Task.objects.filter(tags__isnull=False).values("pk"))

    parts = [_has_tag_q(v) for v in _as_list(value)]
    if not parts or any(p is None for p in parts):
        return None
    if op == "eq":
        return parts[0]
    if op == "neq":
        return ~parts[0]
    if op in ("in",):  # contient l'un
        combined = parts[0]
        for p in parts[1:]:
            combined |= p
        return combined
    if op == "all":  # contient tous
        combined = parts[0]
        for p in parts[1:]:
            combined &= p
        return combined
    if op == "not_in":  # n'en contient aucun
        combined = parts[0]
        for p in parts[1:]:
            combined |= p
        return ~combined
    return None


def _project_q(op, value, now):
    try:
        ids = [int(v) for v in _as_list(value)]
    except (TypeError, ValueError):
        return None
    if op in ("eq", "in"):
        return Q(project_id__in=ids)
    if op in ("neq", "not_in"):
        return ~Q(project_id__in=ids)
    return None


_HANDLERS = {
    "priority": _priority_q,
    "status": _status_q,
    "due": _due_q,
    "tag": _tags_q,
    "tags": _tags_q,
    "project": _project_q,
}


def _collect_included_projects(rules, acc):
    """Ids de listes explicitement incluses (lève l'exclusion « masquée »)."""
    for r in rules or []:
        if not isinstance(r, dict):
            continue
        if "rules" in r:
            _collect_included_projects(r.get("rules"), acc)
            continue
        if r.get("field") in ("project", "list") and r.get("op", r.get("operator")) in ("eq", "in"):
            for v in _as_list(r.get("value")):
                try:
                    acc.add(int(v))
                except (TypeError, ValueError):
                    pass
