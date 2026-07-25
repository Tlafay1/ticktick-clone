# Intégration d'un agent IA (clé d'API + adaptateur)

Le clone n'est pas « IA-natif » (aucune suggestion IA embarquée), mais il est
**entièrement pilotable** par un agent externe via son API REST. Presque toute la
surface d'outils d'un agent type TickTick (créer/maj/compléter/déplacer/épingler des
tâches, projets, dossiers, habitudes, colonnes kanban, tags, stats focus) correspond
à des endpoints existants.

> **Support natif de l'écosystème d'agents (API 0.2.0+)** — l'agent n'a plus besoin
> de poller ni de contourner les limites héritées de TickTick. Voir le
> [changelog API](api-changelog.md) pour le détail : webhooks sortants enrichis
> (diff, acteur, id d'événement, backoff), en-tête `X-Actor` sur toutes les
> écritures, endpoints agrégés `today`/`density`, filtre `overdue`, bulk
> `complete`/`update`/`reschedule`, sessions de focus pilotées serveur
> (`start`/`stop`/`current`), et sérialisation `rrule` corrigée (`null` au lieu de
> `""`).

## 1. Générer une clé d'API

Plutôt que le va-et-vient JWT (access 7 j / refresh 180 j), un agent utilise une
**clé longue durée** :

```bash
# via l'API (authentifié en JWT/session) :
curl -X POST https://tasks.exemple.com/api/api-keys/ \
  -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" \
  -d '{"label": "agent gemini"}'
# -> {"id": 1, "key": "xxx", ...}   (la clé n'est montrée qu'ici, à conserver)
```

Ou depuis l'admin Django (`/admin/accounts/apikey/`).

L'agent envoie ensuite sur **chaque requête** :

```
Authorization: Api-Key <clé>
```

## 2. Brancher l'adaptateur (sans toucher aux outils)

[`integrations/clone_client.py`](../integrations/clone_client.py) est un client async
qui **porte les mêmes noms de méthodes** que `TickTickManager.get_client()` et renvoie
des modèles `ticktick_sdk`. Les fichiers d'outils Gemini (`ticktick_create_task`,
`ticktick_complete_task`, …) fonctionnent donc **sans modification**.

Dans le repo de l'agent :

```python
# chat/services/ticktick_service.py
from integrations.clone_client import CloneClient  # fichier recopié

class TickTickManager:
    _client = None

    @classmethod
    async def get_client(cls):
        if cls._client is None:
            cls._client = CloneClient(
                base_url=os.environ["TICKTICK_CLONE_URL"],
                api_key=os.environ["TICKTICK_CLONE_API_KEY"],
            )
        return cls._client
```

`pip install httpx` côté agent.

## 3. Correspondance des concepts

| Outil de l'agent | Endpoint du clone |
|---|---|
| create/update/delete/move/search/pin task | `/api/tasks/` (complete = `PATCH status:2`, move = `PATCH project` **sans projet source**) |
| today / overdue (un appel) | `/api/tasks/today/` · filtre `/api/tasks/?overdue=1` |
| charge par jour | `/api/tasks/density/?days=N` |
| bulk complete/update/reschedule | `POST /api/tasks/bulk/` (résultat par item) |
| revendiquer une tâche | `PATCH /api/tasks/{id}/ {claimed_by}` → event `task.claimed` |
| projets, dossiers | `/api/projects/`, `/api/project-groups/` |
| colonnes kanban | `/api/sections/` (move = `PATCH section`) |
| habitudes + check-in | `/api/habits/`, `/api/habits/{id}/checkins/` |
| tags | `/api/tags/` |
| pomodoro piloté | `POST /api/focus-sessions/{start,stop}/`, `GET …/current/` |
| stats focus par tag | `/api/focus-sessions/stats/` → `by_tag` |
| webhooks sortants | `/api/webhooks/` (payload v2 : diff, acteur, id d'événement) |
| origine d'une écriture | en-tête `X-Actor: agent:<slug>` → champ `last_actor` |
| journal intime (Obsidian) | `POST /api/journal/entries/` (merge) · `GET /api/journal/entries/{date}/` · `PATCH`/`DELETE /api/journal/moments/{id}` |

## 3 bis. Journal intime → daily note Obsidian (API 0.3.0)

L'agent tient le journal de la journée racontée par l'utilisateur dans la
section `## Journal` de la **daily note Obsidian** (plugin natif Daily Notes),
poussée sur tous les appareils par le service `obsidian-sync`
(voir [deploiement.md](deploiement.md)).

- **Merge incrémental, pas one-shot** : chaque `POST /api/journal/entries/`
  fusionne dans la journée — les listes `highlights` (moments positifs), `lows`
  (négatifs), `anecdotes` et `feelings` (ressentis) **ajoutent** des moments
  horodatés ; `mood` pose ou remplace le ressenti général. L'agent peut donc
  noter un moment à midi, un autre à 17 h et le ressenti global au coucher.
- `date` optionnelle (défaut : aujourd'hui dans le fuseau `tz`, ex.
  `Europe/Paris` ; le fuseau fixe aussi l'affichage des heures dans la note).
- La section est **entièrement re-rendue** à chaque écriture dans un format
  contrôlé (sous-sections par type, moments horodatés, signature de l'acteur) ;
  elle appartient à l'outil — toute édition manuelle y sera écrasée. Le reste
  de la note n'est jamais touché.
- `GET /api/journal/entries/{date}/` renvoie l'état structuré (moments avec
  ids) + le markdown rendu : l'agent relit avant de compléter, et corrige via
  `PATCH`/`DELETE /api/journal/moments/{id}`.
- Chaque écriture émet l'événement webhook `journal.updated`.
- Vault non configuré ou non monté → `503` explicite.

## 4. Limites à connaître

- **Rappels** : créés via l'API, ils ne se déclenchent que si le worker Celery + les
  clés VAPID sont configurés (voir [deploiement.md](deploiement.md)). Sans cela, un
  rappel posé par l'agent reste une donnée inerte.
- **Noms de champs du SDK** : l'adaptateur traduit le snake_case du clone vers les
  noms attendus par `ticktick_sdk` (`desc`, `repeat_flag`, `is_all_day`, `reminders`,
  `project_id`, `column_id`). Si votre version du SDK diffère, ajuster
  `_to_task` / `_from_task_kwargs` dans `clone_client.py`.
- L'adaptateur est un **module de référence** : il vit dans le repo de l'agent, pas
  dans celui du clone.
