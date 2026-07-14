# Changelog API

Journal des évolutions de l'API REST du clone, destiné à la mise à jour des
clients consommateurs (notamment l'écosystème d'agents IA « konofan »). La spec
exécutable vit dans l'OpenAPI (`/api/schema/`, Swagger `/api/docs/`) ; ce fichier
en donne le récit et les points d'attention.

Format : [SemVer](https://semver.org/lang/fr/). Le « **BC** » signale un
changement de comportement à vérifier côté client.

---

## 0.2.0 — Support natif de l'écosystème d'agents

Cible : supprimer le polling 5 min et les contournements côté agent. **Aucun
endpoint existant supprimé ; auth `Api-Key` inchangée.**

### ⚠️ Seul changement de forme (BC mineur)

- **`rrule` : `""` → `null`.** Le champ de récurrence d'une tâche est désormais
  sérialisé `null` quand il est vide (auparavant chaîne vide `""`), ce qui
  faisait crasher des clients qui attendaient `null`. En **entrée**, `null` et
  `""` sont tous deux acceptés (normalisés en base). Le SDK consommateur mappe ce
  champ vers `repeat_flag`/`repeatFrom` : un client qui faisait `d.get("rrule",
  "") or ""` continue de fonctionner. Aucun autre champ n'a changé de forme
  (`timezone_name`, `external_id` restent `""` quand vides — sémantique « texte
  vide » assumée).

### Attribution d'acteur

- En-tête optionnel **`X-Actor`** accepté sur **tous les endpoints d'écriture**
  (create/update/transitions/bulk/delete). Valeur libre (`user`, `agent:<slug>`,
  tronquée à 64 car.) ; défaut `user` si absent.
- Exposé en lecture seule sur la tâche : champ **`last_actor`** (dernière
  écriture). Présent aussi dans chaque entrée d'historique (`GET
  /api/tasks/{id}/activity/` → champ `actor`) et dans chaque payload webhook.
- Permet au consommateur de distinguer « l'agent réagit à une modif utilisateur »
  de « l'agent voit passer sa propre écriture » sans garde applicative.

### Revendication de tâche par un agent

- Champ **`claimed_by`** sur la tâche (`null` quand non revendiquée), modifiable
  en PATCH. Le passage de vide → renseigné émet l'événement `task.claimed`.

### Webhooks sortants — payload v2 (extension additive)

L'enveloppe conserve `event` et `data` (compat récepteurs existants) et ajoute :

```jsonc
{
  "id": "b2f1…",                     // id d'événement stable (idempotence)
  "event": "task.updated",
  "timestamp": "2026-07-14T18:05:00.123456+00:00",  // ISO 8601 + fuseau
  "actor": "agent:gemini",
  "data": { … },                     // snapshot complet de l'entité
  "changes": {                       // présent sur *.updated uniquement
    "title": { "old": "avant", "new": "après" }
  }
}
```

- En-têtes : `X-Webhook-Event`, **`X-Webhook-Id`** (= `id`), `X-Webhook-Signature:
  sha256=<HMAC-SHA256 du corps>` (inchangé).
- **`task.deleted`** transmet désormais le **snapshot complet** de la tâche
  supprimée (auparavant `{ "id": … }` seul).
- **Nouveaux événements** activables : `task.claimed`, `project.created` /
  `project.updated` / `project.deleted`, `habit.checkin`, `pomodoro.started` /
  `pomodoro.stopped` / `pomodoro.completed`. Catalogue à jour :
  `GET /api/webhooks/events/`.
- **Fiabilité** : retries passés à **backoff exponentiel** (max 5 tentatives,
  jitter). Chaque tentative est journalisée (`WebhookDelivery`, avec `event_id`) ;
  consultable via `GET /api/webhooks/{id}/deliveries/`.

### Requêtes riches côté serveur

- `GET /api/tasks/?overdue=1` — tâches en retard (échéance passée + actives).
- **`GET /api/tasks/today/`** — agrège en un appel :
  `{ "date", "today": [...], "overdue": [...] }`. Paramètre `?tz=` (ex.
  `Europe/Paris`) pour la borne de journée ; défaut UTC.
- **`GET /api/tasks/density/?days=N`** — charge par jour :
  `[{ "date": "2026-07-20", "count": 3 }, …]` sur les N prochains jours
  (défaut 7, max 90 ; `?tz=` idem). Inclut les jours à zéro.

### Opérations bulk et ergonomie

- **`POST /api/tasks/bulk/`** — `{ "action": "complete"|"update"|"reschedule",
  "ids": [...], "data": {…} }`. Résultat **par item**, jamais tout-ou-rien :
  `{ "results": [{ "id", "ok", "error"? }, …] }`. `update`/`reschedule` réutilisent
  la validation du `TaskSerializer` (PATCH partiel) ; `reschedule` = raccourci
  `{ start_date, due_date }`. Chaque item modifié émet son webhook.
- **Déplacement de tâche** (rappel, déjà supporté, désormais documenté) :
  `PATCH /api/tasks/{id}/ { "project": <id cible> }`. **Le projet source n'est pas
  requis** — le serveur le résout. (Contrainte : une sous-tâche suit la liste de
  son parent ; la `section` doit appartenir à la liste cible.)

### Pomodoro / sessions de focus pilotées serveur

Le `POST /api/focus-sessions/` (session terminée envoyée en bloc) reste inchangé.
Nouvelles actions pour piloter une session en cours :

- **`POST /api/focus-sessions/start/`** — `{ planned_seconds?, task?, mode?,
  session_type? }` → 201. **409** si une session est déjà en cours. Émet
  `pomodoro.started`.
- **`POST /api/focus-sessions/stop/`** — clôt la session en cours (calcule
  `duration_seconds`). **409** si aucune. Émet `pomodoro.completed` si la durée
  prévue est atteinte (ou si `planned_seconds` absent), sinon `pomodoro.stopped`.
- **`GET /api/focus-sessions/current/`** — 200 avec la session en cours, **204**
  sinon.
- Historique filtrable : `GET /api/focus-sessions/?start_after=…&start_before=…`
  (bilans quotidiens). Nouveau champ sérialisé `planned_seconds`.

### Rappels de conformité (déjà en place, garantis)

- **Dates** : ISO 8601 avec fuseau partout (DRF + `USE_TZ`, stockage UTC).
- **IDs** : entiers auto-incrémentés, stables.
- **OpenAPI** : `VERSION` 0.1.0 → **0.2.0**. Le schéma documente désormais le
  schéma de sécurité `Api-Key`.
