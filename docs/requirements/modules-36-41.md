# Modules 36 à 41 — Méthode d'organisation (Jalon 9)

Absents de TickTick : ces modules outillent la **méthode d'organisation personnelle**
de l'utilisateur (profil procrastinateur, méthodes TDAH efficaces). Principe directeur :
**les décisions se prennent à froid (revue), l'exécution ne demande aucune décision**.
Démarrer coûte un geste, renoncer est un choix explicite, la dette de retard ne
s'accumule jamais, le ton n'est jamais culpabilisant.

Critères d'acceptation testables ; `[J9]` = jalon 9 ; spec :
`backend/spec/test_jalon9_methode.py` (+ vitest pour la logique pure côté web).

**Règles fixes** (constantes, non configurables — « décidées une fois pour toutes ») :
contrat de démarrage **10 min** ; relance **15 min** après l'heure d'un créneau non
démarré ; créneau **raté** 15 min après sa fin ; **3** reports → tâche bloquée ;
amnistie des retards de **plus de 7 jours** ; montée de niveau après **2 semaines ≥ 80 %**,
descente après **2 semaines < 50 %**.

**Configurable** (`MethodConfig`) : niveau, jokers par mois (défaut 2), limite de tâches
« Aujourd'hui » (défaut 3), jour + heure de la revue hebdo (défaut dimanche 18:00),
pause jusqu'à une date. Les heures sont **murales** : elles s'interprètent dans
`UserSettings.timezone`.

---

## Module 36 — Créneaux `[J9]`

- **(36.1) Créneau récurrent** : jour de semaine (lundi = 0) + heure + durée (défaut 25 min)
  + objectif optionnel (une liste ; vide = « auto ») + type `work` | `buffer` (tampon).
  CRUD `/api/slots/`. La liste ciblée doit appartenir à l'utilisateur.
- **(36.2) Occurrences** : chaque créneau actif produit une occurrence datée par semaine
  (`/api/slot-occurrences/?start=&end=`), matérialisée à la demande et par le tick
  minute. Statuts : `planned`, `honored`, `missed`, `excused` (+ raison `joker` /
  `rouge` / `pause`), `recovered` (raté puis rattrapé), `free` (tampon inutilisé).
  Modifier ou supprimer un créneau ne réécrit pas l'historique passé.
- **(36.3) Prochaine action** : une occurrence propose une tâche — celle assignée à
  l'occurrence (pré-planifiée en revue), sinon la première tâche ouverte (ordre manuel)
  de l'objectif du créneau, sinon de l'objectif actif le mieux classé. Jamais une
  proposition non validée (M39).
- **(36.4) Démarrer en un geste** : `POST /api/slot-occurrences/{id}/start/` honore
  l'occurrence (même en retard, tant que c'est le même jour), fixe la tâche travaillée
  et lance une session focus de **10 min** (contrat), ou `minutes` si fourni.
  Démarrer est accepté dès 60 min avant l'heure.
- **(36.5) Relances** (tick minute) : à l'heure → événement `slot.due` (+ notification
  « C'est l'heure : <prochaine action> ») ; à +15 min sans démarrage → `slot.nudge`
  (version 2 minutes) ; 15 min après la fin → `missed` + `slot.missed`. Une seule fois
  chacun, jamais au-delà (pas de harcèlement).
- **(36.6) Tampon** : un créneau raté est automatiquement **reporté au prochain tampon**
  libre de la semaine (zéro décision). Démarrer ce tampon marque le raté `recovered`.
  Un tampon qui n'a rien à rattraper est du **temps libre** (il ne compte jamais dans
  le score) ; non utilisé, il passe `free`.
- **(36.7) Jokers** : `POST /api/slot-occurrences/{id}/joker/` excuse une occurrence
  prévue ou ratée sans pénalité ; quota mensuel (`jokers_per_month`), refus explicite
  au-delà (« Plus de joker ce mois-ci »).

## Module 37 — Couleur du jour & pause `[J9]`

- **(37.1) Couleur du jour** : `PUT /api/method/day/` `{color: green|orange|red}` (défaut
  aujourd'hui). **Rouge** excuse les créneaux restants du jour (raison `rouge`) ; revenir
  au vert/orange les remet en `planned` s'ils ne sont pas passés. **Orange** = version
  minimale (exposée aux clients/agents). Événement `day.color`.
- **(37.2) Pause** : `MethodConfig.pause_until` excuse les créneaux (raison `pause`) et
  suspend relances et événements jusqu'à cette date incluse.
- **(37.3) Tableau de bord du jour** : `GET /api/method/today/` → couleur, pause,
  occurrences du jour avec prochaine action, nombre de tâches d'aujourd'hui vs limite,
  jokers restants, niveau.

## Module 38 — Objectifs & frigo `[J9]`

- **(38.1)** Une liste peut être **objectif actif** ou **au frigo** (`Project.objective` :
  `""` | `active` | `fridge`). **2 objectifs actifs maximum** : activer un 3e est refusé
  (« Range d'abord un objectif au frigo »).
- **(38.2) Progression** : chaque liste expose `tasks_total` / `tasks_done` (tâches
  terminées vs terminées + ouvertes, hors corbeille/archives/propositions/abandonnées).

## Module 39 — Propositions de l'IA `[J9]`

- **(39.1)** Une tâche créée avec `proposed=true` (typiquement par l'agent planificateur)
  est **en attente de validation** : exclue des listages par défaut, des smart lists, de
  `today`/`density` et des prochaines actions ; visible via `?proposed=1`.
- **(39.2)** Accepter = `PATCH {proposed: false}` (ou bulk `update`) ; refuser = suppression
  définitive. Le compteur de propositions est exposé dans la revue et le tableau de bord.

## Module 40 — Retard & procrastination `[J9]`

- **(40.1) Report** : repousser l'échéance d'une tâche qui était due aujourd'hui ou en
  retard (ou la retirer) incrémente `postpone_count`. Planifier une tâche future n'est
  pas un report.
- **(40.2) Bloquée** : au 3e report, la tâche est **bloquée** (`?blocked=1`), événement
  `task.blocked` (une fois).
- **(40.3) Diagnostic** : `POST /api/tasks/{id}/diagnose/` `{reason}` parmi
  `boring` (ennuyeuse), `unclear` (floue), `too_big` (trop grosse), `unpleasant`
  (désagréable), `useless` (plus utile). Renvoie un **remède** concret ; `useless` abandonne
  la tâche (won't do) ; les autres remettent le compteur à zéro et mémorisent la raison
  (`blocker`). Événement `task.diagnosed` (l'agent planificateur applique le remède).

## Module 41 — Revue hebdo & niveaux `[J9]`

- **(41.1) Bilan** : `GET /api/method/review/?week=` → score de la semaine
  (créneaux de travail honorés + rattrapés / prévus hors excusés), occurrences,
  **réalisations** (tâches terminées), tâches bloquées, candidates à l'amnistie (retard
  > 7 j), compte Inbox et propositions, couleurs des jours, jokers restants, niveau et
  **suggestion** (`up` / `down` / `keep`) selon la règle des 2 semaines.
- **(41.2) Validation** : `POST /api/method/review/` applique l'**amnistie** (les retards de
  plus de 7 jours perdent leur échéance et retournent dans leur liste — sans compter
  comme report), fixe le niveau choisi, fige le score de la semaine. Événement
  `review.completed`. Idempotent par semaine.
- **(41.3) Rendez-vous de revue** : au jour/heure configurés → `review.due` (+ notification) ;
  2 h avant → `review.upcoming` (l'agent planificateur prépare ses propositions).
- **(41.4) Limite « Aujourd'hui »** : le client affiche le compteur `n / today_limit` et
  avertit au-delà (règle douce, jamais bloquante).
