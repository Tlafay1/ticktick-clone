# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# Projet : clone TickTick — guide d'implémentation

Clone **self-hosted, mono-utilisateur** de TickTick. Le dépôt contient déjà les
**fondations + le Jalon 1** (cœur des tâches) et une **spec vivante exécutable**
qui décrit *tout* le reste à construire. Mission : convertir les stubs `skip`/
`todo` en fonctionnalités, jalon par jalon, en les faisant passer au vert.

## Source de vérité

Les requirements complets (PRD corrigé, toutes décisions incluses) sont **dans le
dépôt** : [docs/requirements/](docs/requirements/). Tu n'as JAMAIS besoin qu'on te
redonne les requirements — tout est là, organisé par module avec critères
d'acceptation. La carte module → jalon → spec est dans
[docs/requirements/README.md](docs/requirements/README.md).

## Procédure principale (concevoir → tester → implémenter)

1. **Jalon courant** : backlog ordonné = `cd backend && uv run pytest -ra`
   (lignes `SKIPPED … Jalon N`). Pour chaque comportement à livrer :
2. **Lire l'exigence** dans [docs/requirements/](docs/requirements/) (le module `MNN`
   du nom du test). C'est le « quoi » détaillé. Le docstring du stub en est le résumé.
3. **Concevoir si besoin** : pour les jalons ≥ 2, le modèle/serializer/endpoint
   n'existe peut-être pas encore. Conçois-le à partir de l'exigence en suivant les
   conventions ci-dessous (gabarit d'app, `OwnedModelViewSet`, valeurs canoniques),
   puis `makemigrations`.
4. **Écrire le vrai test** : retire le `@pytest.mark.skip`, remplace le corps
   `raise NotImplementedError` par des **assertions réelles** dérivées des critères
   d'acceptation de l'exigence (s'inspirer de `test_jalon1_acceptance.py`).
5. **Implémenter** jusqu'au vert.
6. **Web** : remplace les `it.todo(...)` de [web/src/spec/acceptance.spec.ts](web/src/spec/acceptance.spec.ts)
   par de vrais tests au fil de l'eau.
7. **Natif & UI gestuelle** : pas d'auto-test → cocher [docs/acceptance-checklist.md](docs/acceptance-checklist.md).

## Définition de « fini » (done-gate — à faire passer AVANT de dire « terminé »)

Un comportement n'est « fait » que si **tout** ce qui suit est vert :
```bash
cd backend && uv run pytest          # tous verts (aucun échec, aucune erreur)
cd web && npm run build              # vue-tsc (typecheck) + vite build — DOIT passer
cd web && npm test                   # vitest verts
```
**Pièges à éviter** : `npm test` (vitest) ne typecheck PAS — un test vert ne garantit
pas que l'app compile ; c'est `npm run build` qui le garantit. Ne jamais rendre un
test vert en l'affaiblissant : il doit refléter le critère d'acceptation de l'exigence.

**Règle d'or : aucun comportement « fait » sans son test fidèle vert ET le build vert.**
Un jalon est terminé quand son fichier spec n'a plus aucun `skip`, que la done-gate
est verte, et que les items natifs/UI du jalon sont cochés dans la checklist.

## Périmètre — ne PAS réintroduire

Tracé dans [backend/spec/test_scope_cuts.py](backend/spec/test_scope_cuts.py).
**Mono-utilisateur** : aucune collaboration. **Coupé** : module Notes entier,
saisie/dictée vocale, pause focus sur appel, captcha / rate-limiting / vérification
d'email, toutes les intégrations externes (OAuth Google/Outlook, CalDAV,
email-to-task, IA, Notion, Apple Health), web clipper, wearables, clients
iOS/macOS/Linux. **Seul l'abonnement ICS read-only est gardé.** En cas de doute,
vérifier `test_scope_cuts.py` avant d'implémenter.

## Stack & lancement

Backend Django 5 + DRF (`backend/`, Channels & Celery à venir J4/J5) · Web Vue 3 +
TS + Vite + Pinia (`web/`) · Mobile Capacitor/Android (`mobile/`, J6) · Desktop
Electron/Windows (`desktop/`, J7).

```bash
docker compose up -d                               # Postgres + Redis (requis pour les tests)
cd backend && uv sync && uv run python manage.py migrate && uv run python manage.py runserver
cd web && npm install && npm run dev               # proxy /api → :8000
```
API browsable `:8000/api/` · Swagger `:8000/api/docs/` · admin `:8000/admin/`.

```bash
cd backend && uv run pytest        # 39 verts / 163 skip ; Postgres doit tourner
cd web && npm test                 # vitest : verts + todo
```

## Conventions backend

- Apps existantes : `accounts` (User email-login + UserSettings), `projects`
  (Project=liste, ProjectGroup=dossier, Section=colonne kanban), `tasks` (Task,
  CheckItem, Comment, ActivityLog), `tags`. Apps à créer pour les jalons suivants
  (`filters`, `habits`, `focus`, `calendars`, `notifications`, `stats`, `sync`) :
  même gabarit (`apps.py`/`models.py`/`serializers.py`/`views.py`/`urls.py`/
  `migrations/__init__.py`/`admin.py`/`tests/`).
- **Isolation** : hériter de `OwnedModelViewSet` ([backend/apps/projects/views.py](backend/apps/projects/views.py)).
  Valider dans les serializers que chaque FK (project, parent, tags) appartient à l'utilisateur.
- **Auth** JWT ; inscription ouverte ; un signal crée UserSettings + l'**Inbox**
  (non supprimable/renommable).
- **Valeurs canoniques** ([backend/apps/tasks/models.py](backend/apps/tasks/models.py)) :
  `status` 0=normal / 2=completed / -1=wont_do ; `priority` 0/1/3/5
  (couleurs none=gris, low=bleu, **medium=jaune**, high=rouge) ;
  `MAX_SUBTASK_DEPTH=5` ; corbeille 30 j (1er delete→corbeille, 2e/`?permanent=1`→définitif).
- **3 tiers de checklist** : Tier 1 `Task.parent` (sous-tâches datables) ; Tier 2
  `CheckItem` (léger, auto-trié en bas si coché) ; Tier 3 checkboxes markdown (front).
- **Smart lists** : pas d'endpoints dédiés — composées via query params sur
  `/api/tasks/` (`smart=1`, `status`, `due_before`/`due_after`, `ordering`, `q`).
  Exemples : [backend/spec/test_jalon1_acceptance.py](backend/spec/test_jalon1_acceptance.py).
- **Ordre manuel** : `sort_order` espacé de `SORT_STEP`, insérer entre deux valeurs.
- **Fixtures** ([backend/conftest.py](backend/conftest.py)) : `user`, `inbox`, `api`.

## Conventions web

- `src/types.ts` reflète les modèles backend (garder synchro).
- `src/api/` : `client.ts` (fetch + refresh JWT) et `index.ts` (un objet par
  ressource) — pas de `fetch` ailleurs.
- `src/lib/` : logique pure **testée** (`nlp.ts`, `markdown.ts`, `dates.ts`) ; y
  ajouter filtre booléen, projection de récurrence, file offline + tests vitest.
- `src/platform/` (J5+) : adaptateurs notifications/stockage/hotkeys/tray (interface
  unique, impl `web.ts`/`capacitor.ts`/`electron.ts`).

## Style

Commentaires et chaînes UI **en français**. Coller au style alentour. Système
ouvert, aucune friction. Référencer les fichiers en liens markdown cliquables.