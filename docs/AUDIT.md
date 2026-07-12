# Audit du clone TickTick — état, fidélité, roadmap

> Audit réalisé en juillet 2026. Méthode : lecture exhaustive du code (10 agents
> parallèles par sous-système) + recherche factuelle croisée sur la **vraie**
> application TickTick (centre d'aide officiel, blog, bases de raccourcis, revues),
> avec niveau de confiance par fait. Ce document est la référence vivante de
> l'écart au produit cible ; il est mis à jour au fil des livraisons.

## 1. Résumé exécutif

Le clone est **beaucoup plus avancé que « démarré à l'arrache »** : le backend
(Django 5 / DRF) couvre fidèlement le cœur TickTick (tâches, listes, dossiers,
sections/kanban, tags hiérarchiques, récurrence RRULE, rappels, corbeille,
habitudes, focus, stats, countdown, sync WebSocket, offline, Web Push, clés
d'API). Le web (Vue 3 / Pinia) reproduit la structure 3 colonnes de TickTick avec
un panneau de détail riche. Les **clients natifs (Android / Windows) sont des
squelettes** non fonctionnels.

Ce qui manquait le plus et a été traité pendant cet audit :

- **CI absente** → workflow GitHub Actions (backend pytest+ruff avec Postgres/Redis,
  web vue-tsc+vitest+build) fusionné depuis une branche restée en attente.
- **Failles d'isolation en écriture** (Section, Task.section, Project.group non
  validés) → corrigées + testées.
- **Bugs de fidélité** (deep link tâche mort, QuickAdd n'envoyait pas les tags ni
  ne respectait `^Liste`, recherche laissant des résultats périmés, habitudes
  numériques multi-log jamais « faites », consumer WebSocket qui crashait sur un
  refresh token) → corrigés + testés.
- **Trous de couverture** (consumer WebSocket, Web Push, `/api/me/`, composants
  Vue) → premiers tests ajoutés (montage de composants via `@vue/test-utils`,
  `pytest-asyncio` pour le WS).

Restent, par ordre de valeur : **features développeur** (webhooks, FCM,
élargissement de l'API pour n8n/IA), **fidélité fine** (raccourcis clavier,
vue jour calendrier, pause/reprise du focus, édition d'habitude, câblage de l'UI
des smart lists personnalisées), **E2E Playwright**, et la **réalisation réelle
des clients natifs**.

## 2. Décisions de conception confirmées par la recherche

Ces points sont souvent supposés « à corriger » mais sont en réalité **corrects**
ou **des choix maison assumés** — à ne pas « fidéliser » par erreur :

| Sujet | Réalité TickTick (sourcée) | Conséquence pour le clone |
|---|---|---|
| Feedback de complétion | Son configurable ; **pas** de confetti ni toast « Undo » documentés | Garder le feedback minimal (son) — ne pas inventer d'animation |
| `planned_date` | **N'existe pas** dans TickTick (uniquement due / start / end / all-day) | C'est un **ajout volontaire** de l'utilisateur → à **exposer** côté web, pas à retirer |
| Corbeille 30 j | Aucune durée de rétention documentée | Décision maison assumée — OK |
| Token liste Quick Add | `~Liste` aujourd'hui (`^` obsolète) | Le clone accepte `~` **et** `^` — compatible |
| Priorité Quick Add | `!` ouvre un **picker** (pas `!1`) | Le clone utilise `!high`/`!!!` (adaptation texte) — acceptable |
| Rappels max | **5 / tâche** (Free 2 / Premium 5) | Le clone plafonne à 5 — fidèle |

Sources principales : help.ticktick.com (Task Details, Multilevel Tasks, Set Up
Recurring Tasks, Smart Recognition, Constant Reminder, Appearance, Widgets,
Desktop Shortcuts), blog.ticktick.com, usethekeyboard/quickref (raccourcis).

## 3. État par domaine

Légende : ✅ complet · 🟡 partiel · 🟠 stub · ⛔ absent · 🐛 cassé.

### Backend
- ✅ **Comptes / auth** : login e-mail, JWT (register/token/refresh), signal Inbox+settings, **clés d'API** (`Authorization: Api-Key …`, pensées pour agents IA).
- ✅ **Tâches** : statuts 0/2/-1, priorités 0/1/3/5, dates due/start/end/**planned**/all-day, sous-tâches ≤5 niveaux, CheckItem, commentaires, ActivityLog, corbeille 30 j, tri manuel, recherche, smart lists par query params.
- ✅ **Organisation** : Project/ProjectGroup/Section, kanban (CRUD/reorder/move/done), tags hiérarchiques + merge.
- ✅ **Moteur de filtres** des smart lists personnalisées (`apps/projects/filters.py`) — **existe désormais** (fusionné), mais l'UI ne l'ouvre pas encore (cf. §5).
- 🟡 **Récurrence** : RRULE (daily/weekly/monthly/yearly, INTERVAL, BYDAY, UNTIL/COUNT, repeat_from completion). Manque « dates spécifiques » (liste de dates).
- 🟡 **Calendriers ICS** : CRUD de l'abonnement seul — **aucun parsing/fetch/refresh** des événements (`last_synced_at` mort, pas de lib ICS). L'exigence « afficher les événements .ics » n'est pas satisfaite.
- 🟡 **Habitudes** : CRUD/presets/check-ins/streaks OK ; agrégation numérique **corrigée** ; streak encore **aveugle à la fréquence** (specific_days/interval/weekly_goal notés comme quotidiens) ; rappels d'habitude stockés mais **jamais diffusés** (pas de tâche Celery).
- 🟡 **Focus / Stats / Sync** : pomodoro + sessions ; stats (score, heatmap, mensuel, par liste) ; sync WebSocket (consumer **corrigé**) + Web Push.
- ⛔ **Webhooks** : inexistants (à construire — §6).

### Web (Vue 3)
- ✅ Structure 3 colonnes, détail de tâche riche, menus contextuels, thèmes clair/sombre/auto + accents, drag & drop, offline + rejeu, sync temps réel.
- ✅ Vues : listes/smart lists, Inbox, corbeille, tags, Kanban, Eisenhower, Habitudes, Stats, Countdown, Réglages.
- 🟡 **Calendrier** : semaine/mois/agenda (**pas de vue jour**) ; `week_start` **ignoré** (lundi codé en dur) ; événements ICS non rendus.
- 🟡 **Focus** : la « pause » est en fait un **stop+reset** (pas de reprise) ; sons d'ambiance décoratifs ; stats de focus jamais affichées.
- 🐛 **Smart lists personnalisées** : `ProjectEditor`/`FilterEditor` **injoignables** (`editingProject` jamais assigné) → l'UI du moteur de filtres n'est pas câblée.
- 🟡 **types.ts** : omet `planned_date`/`end_date`/`reminders` sur `Task` (pourtant sérialisés) ; pas de client `calendar-subscriptions`.
- ⛔ **Raccourcis clavier** : aucun (TickTick en a une trentaine).

### Clients natifs
- 🟠 **Android (Capacitor)** : `capacitor.config.ts` seul ; `mobile/android/` vide ; aucun code Kotlin (widgets, Quick Ball, gestes, géofencing) ; pas de `package.json`.
- 🟡/🐛 **Windows (Electron)** : shell réel (tray, hotkey, mini quick-add, notifications) ; le **packaging a été corrigé** (dist embarqué, serveur local, assets) via la branche fusionnée ; reste à câbler `window.electronAPI` côté renderer et à réconcilier le hotkey global (`Shift+Alt+A` chez TickTick).

### Infra
- ✅ Compose dev/prod, Dockerfiles, nginx, `/health/`, **CI GitHub Actions**.
- 🟡 Compose prod : rappels Celery nécessitent worker+beat (présents en prod, absents du compose dev).
- 🐛 **Médias en prod** : servis via `static()` (no-op si `DEBUG=0`) → pièces jointes en 404 derrière nginx. **À corriger** (servir `/media/` proprement).

## 4. Corrections livrées pendant l'audit

| Commit | Objet |
|---|---|
| `chore` | Suppression de l'outillage aider obsolète (scripts, configs, MISSING.md, doc). |
| `fix(api)` | Isolation en écriture : `Section.project`, `Task.section` (+ cohérence section⊂liste), `Project.group` ; filtre `?parent=` des tags. |
| `fix(web)` | Deep link `/task/:id` ; QuickAdd envoie les tags + respecte `^Liste` + titre non vide ; recherche recharge la vue à l'effacement. |
| `fix(habits)` | Agrégation des logs numériques du jour pour la complétion. |
| `test+fix` | Consumer WS (rejet refresh token) + tests ; Web Push (`notify_user`, purge 410) ; `/api/me/`. |

Base de tests : **backend 198 verts** (39 au départ), **web 172 verts** + 13 todo.
Infra de test de composants ajoutée (`@vue/test-utils` + happy-dom), `pytest-asyncio`
+ `daphne` pour le WebSocket.

## 5. Écarts de fidélité restants (priorisés)

### ✅ Traités depuis l'audit (juillet 2026)
- ~~UI des smart lists personnalisées~~ : entrée « Modifier » du menu contextuel → `ProjectEditor`/`FilterEditor` atteignables (le vocabulaire d'opérateurs était déjà aligné par le moteur fusionné).
- ~~`planned_date`/`end_date`/`reminders` dans types.ts~~ (le détail de tâche reste à enrichir pour planned/end).
- ~~Médias en production~~ (route `/media/` servie hors DEBUG).
- ~~week_start + agenda 30 j~~ ; ~~pause/reprise du focus~~ ; ~~raccourcis clavier~~ (Ctrl+Maj+A, Ctrl+F, Ctrl+Maj+M, Ctrl+Alt+T/N/1/C, ?, Échap) ; ~~listes archivées/désarchivage~~ ; ~~fusion de tags (UI)~~ ; ~~persistance du repli des dossiers~~ ; ~~sous-tâches imbriquées en liste~~ ; ~~refonte du panneau de détail~~ ; ~~N+1 rappels~~.
- ~~Événements ICS~~ : chaîne complète (parsing icalendar + dépliage RRULE, refresh Celery horaire + action `/refresh/`, endpoint `/api/calendar-events/`, réglages + rendu calendrier).

### P1 — restant
1. **Rappels d'habitude non diffusés** (aucune tâche Celery) — la fonctionnalité est inerte.

### P2 — restant
2. **Vue calendrier Jour** (semaine/mois/agenda existent).
3. **Streak d'habitude conscient de la fréquence** (specific_days/interval/weekly_goal) + fréquences avancées dans le formulaire.
4. **Édition** d'habitude et de countdown (create/pin/delete seulement) ; **sons d'ambiance** du focus factices ; **stats de focus** jamais affichées.
5. **Exposer planned_date/end_date** dans le panneau de détail (champs déjà typés).

### P3 — polish restant
6. Multi-sélection de tâches + actions groupées ; historique de recherche exposé.
7. Convergence des « dates spécifiques » de récurrence ; réordonnancement des dossiers.

## 6. API développeur & webhooks (à construire)

Objectif : dépasser l'Open API officielle de TickTick (limitée à tasks/projects,
OAuth2, **pas de webhooks**) pour l'intégration n8n / IA / scripts.

- **Auth** : ✅ clés d'API (PAT) déjà en place — révocables, `Api-Key` header. À
  compléter : page de doc, scopes optionnels, `last_used_at` déjà présent.
- **Webhooks** (à créer, app `webhooks`) :
  - Modèle `Webhook(user, url, events[], secret, is_active)` + journal de livraison.
  - Événements : `task.created/updated/completed/deleted`, `habit.checked`, etc.
  - Livraison **asynchrone** (Celery) avec **signature HMAC** (`X-Signature`) et
    retries — idéal pour n8n (nœud Webhook) et Home Assistant.
  - CRUD `/api/webhooks/` + endpoint de test (« ping »).
- **DX** : Swagger déjà exposé (`/api/docs/`) ; ajouter des exemples n8n et un
  client de référence (`integrations/clone_client.py` existe, à documenter/tester).
- **FCM** (Android) : projet Firebase fourni → adaptateur d'envoi push côté backend
  (en complément du Web Push VAPID) + plugin Capacitor côté mobile.

## 7. Tests & CI

- **CI** (`.github/workflows/ci.yml`) : job backend (uv, ruff, pytest + services
  Postgres/Redis), job web (npm ci, vue-tsc, vitest, vite build). **À étendre** :
  Playwright E2E (navigateur réel), et à terme lint/format front (eslint/prettier).
- **Trous de couverture restants** : `client.ts` (refresh JWT single-flight, file
  offline), mutations de stores Pinia, davantage de composants, parsing/refresh ICS,
  streak d'habitude par fréquence, tâches Celery (rappels/purge).

## 8. Périmètre — hors sujet (ne pas réintroduire)

Mono-utilisateur : aucune collaboration. Coupés : module Notes, dictée vocale,
captcha/rate-limit/vérif e-mail, intégrations externes (OAuth Google/Outlook,
CalDAV, email-to-task, IA tierces, Notion, Apple Health), web clipper, wearables,
iOS/macOS/Linux. **Seul l'abonnement ICS read-only est gardé.** Référence :
`backend/spec/test_scope_cuts.py`.
