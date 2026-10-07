# Changelog API

Journal des évolutions de l'API REST du clone, destiné à la mise à jour des
clients consommateurs (notamment l'écosystème d'agents IA « konofan »). La spec
exécutable vit dans l'OpenAPI (`/api/schema/`, Swagger `/api/docs/`) ; ce fichier
en donne le récit et les points d'attention.

Format : [SemVer](https://semver.org/lang/fr/). Le « **BC** » signale un
changement de comportement à vérifier côté client.

---

## 0.3.0 — Méthode d'organisation (créneaux, revue, propositions)

Cf. [requirements/modules-36-41.md](requirements/modules-36-41.md). **Un BC** :
les propositions sont exclues des listages par défaut (voir ci-dessous).

### Créneaux (M36)
- **`/api/slots/`** (CRUD) : `{weekday (lundi=0), start_time, duration_minutes (25),
  project|null (null = objectif actif auto), kind: work|buffer}`.
- **`GET /api/slot-occurrences/?start=&end=`** (défaut : semaine courante) :
  `{id, slot, date, start_at, end_at, kind, status (planned|honored|missed|excused|
  recovered|free), excuse_reason (joker|rouge|pause), task, next_action {id,title,project}|null,
  started_at, focus_session, recovers}`. **`PATCH {task}`** pré-planifie la tâche d'une occurrence.
- **`POST …/{id}/start/`** `{task?, minutes?}` : honore + focus de 10 min (contrat) ;
  rattache la session focus déjà en cours s'il y en a une. 400 hors du jour / > 1 h d'avance.
- **`POST …/{id}/joker/`** : excuse sans pénalité, quota mensuel (400 « Plus de joker ce mois-ci »).

### Jour, réglages, revue (M37, M41)
- **`GET/PATCH /api/method/config/`** : `level, jokers_per_month, today_limit,
  review_weekday, review_time, pause_until`.
- **`GET /api/method/today/`** : couleur, pause, niveau, `today_count`/`today_limit`,
  jokers restants, `proposals_count`, occurrences du jour (avec `next_action`).
- **`PUT /api/method/day/`** `{color: green|orange|red, date?}`.
- **`GET /api/method/review/?week=`** : bilan (score `{honored, decided, rate}`,
  occurrences, `completed`, `focus_minutes`, `blocked`, `amnesty`, `inbox_count`,
  `proposals_count`, `day_colors`, `jokers_remaining`, `level`, `suggestion` up|down|keep,
  `completed_at`). Sans `week` : la dernière revue arrivée (ou dans les 2 h).
- **`POST /api/method/review/`** `{week?, level?, amnesty=true, notes?}` : amnistie les
  retards > 7 j (échéance retirée, pas compté comme report), fixe le niveau, fige le
  score. Idempotent par semaine.

### Tâches & listes (M38–M40)
- Tâche : **`proposed`** (écrivable), **`postpone_count`**, **`blocker`** (lecture seule).
- ⚠️ **BC** : `GET /api/tasks/` **exclut les propositions** (`proposed=true`) ; `?proposed=1`
  ne liste qu'elles. Exclues aussi de `today`, `density`, des prochaines actions. Accepter
  = `PATCH {proposed: false}` ; refuser = `DELETE ?permanent=1`.
- `?blocked=1` : tâches reportées 3 fois. **`POST /api/tasks/{id}/diagnose/`**
  `{reason: boring|unclear|too_big|unpleasant|useless}` → `{task, remedy}`.
- Liste : **`objective`** (`""`|`active`|`fridge`, 2 actifs max → 400), **`tasks_total`**,
  **`tasks_done`**.

### Nouveaux événements webhook
`slot.due`, `slot.nudge`, `slot.missed`, `slot.started` (payload = occurrence ;
`slot.missed` ajoute `recovery` = `{occurrence, date, start_at}` du tampon de report, ou `null`),
`day.color` (`{date, color}`), `review.upcoming` / `review.due` (`{week_start, review_at}`),
`review.completed` (bilan), `task.blocked` (tâche), `task.diagnosed` (`{task, reason,
remedy}`). Acteur `system` pour ceux émis par le tick minute. Un webhook abonné à une
liste explicite d'événements doit les ajouter pour les recevoir.

---

## 0.2.1 — Rappels fiables, fuseau horaire

**Purement additif, aucun BC.**

- **`GET/PATCH /api/me/settings/` → `timezone`** (IANA, ex. `Europe/Paris`,
  `""` = inconnu → UTC serveur). Les clients le renseignent automatiquement ;
  les heures « murales » (rappels d'habitude, futurs créneaux) s'y interprètent.
  Valeur inconnue → 400.
- **`GET /api/habits/` → `due_today`, `completed_today`** (lecture seule, « aujourd'hui »
  au sens du fuseau de l'utilisateur).
- **`POST /api/push/fcm-token/` → `local_reminders`** (booléen, défaut `false`) :
  l'appareil programme ses rappels en local, le serveur ne les lui pousse plus
  en FCM (pas de doublon). Les autres pushs FCM restent envoyés.
- **Dispatch des rappels** : un rappel de tâche récurrente ou reportée est réarmé
  pour la nouvelle échéance (il ne partait qu'une fois) ; un rappel de plus de
  2 h de retard est marqué envoyé sans notifier ; un canal en échec ne bloque plus
  les autres (cause des rappels « en boucle »). Le payload Web Push porte un `tag`.

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
