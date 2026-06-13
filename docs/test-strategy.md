# Stratégie de test — clone TickTick

La suite est une **spec vivante** : elle décrit *tout* le périmètre du PRD corrigé
et sert de définition de « terminé ». Elle est verte là où la fonctionnalité
existe, et `skip`/`todo` là où elle reste à construire. Chaque jalon livré
convertit ses stubs en tests réels.

> Le « quoi » détaillé (critères d'acceptation par module) vit dans
> [requirements/](requirements/). Les tests vérifient ces exigences ; les deux se
> lisent ensemble.

**Done-gate** (avant de dire « terminé ») : `cd backend && uv run pytest` **et**
`cd web && npm run build` **et** `cd web && npm test` doivent être verts. `npm test`
ne typecheck pas — seul `npm run build` garantit que l'app compile.

## Les trois couches

| Couche | Outil | Emplacement | Rôle |
|--------|-------|-------------|------|
| **Unitaire** | pytest / vitest | `backend/apps/*/tests/`, `web/src/lib/__tests__/` | Logique fine, déjà implémentée. Toujours verte. |
| **Acceptation (spec map)** | pytest / vitest | `backend/spec/`, `web/src/spec/` | 1 test nommé par comportement du PRD, organisé par jalon. Vert = livré, `skip`/`todo` = planifié. |
| **Checklist manuelle** | Markdown | `docs/acceptance-checklist.md` | Natif & UI lourde (gestes Android, tray Electron, drag-drop calendrier, widgets) — vérifié à la main + smoke e2e léger quand la feature atterrit. |

## Conventions de la spec map

- **Backend** : un stub planifié est `@pytest.mark.skip(reason="Jalon N — …")`
  avec un *docstring qui décrit précisément le comportement attendu* (c'est lui,
  le contrat durable) et un corps `raise NotImplementedError` qui sert de
  **tripwire** : retirer le `skip` sans écrire le test fait échouer le test, donc
  on ne peut pas « passer au vert » sans réellement implémenter la vérification.
- **Web** : `it.todo("…")` (vitest) — pas de corps, donc pas de faux positif.
- **Traçabilité PRD** : chaque test est nommé `test_mNN_<comportement>` ; `NN` est
  le numéro de module du PRD. On retrouve ainsi n'importe quelle exigence.
- **Features coupées** : documentées dans `backend/spec/test_scope_cuts.py` avec la
  raison (mono-utilisateur, hors périmètre client, hallucination du PRD…). Elles
  font partie de la définition de « terminé » en creux : on sait qu'elles sont
  délibérément absentes, pas oubliées.

## Lire la carte de couverture

```bash
cd backend && uv run pytest            # -ra affiche le résumé des skip = le reste à faire
cd backend && uv run pytest spec/ -ra  # uniquement la carte d'acceptation
cd web && npm test                     # vitest : todo affichés en jaune
```

Le résumé `SKIPPED [n] spec/test_jalonN_*.py: Jalon N — …` est, littéralement, le
backlog ordonné par jalon.

## Mapping jalon → fichiers spec

| Jalon | Backend spec | Contenu |
|-------|--------------|---------|
| 1 | `test_jalon1_acceptance.py` | **Réel/vert** : cœur tâches, smart lists, tags plats, recherche, corbeille, Won't Do, 3 tiers de checklist, commentaires. |
| 2 | `test_jalon2_organization.py` | Dossiers, DnD, tags hiérarchiques, smart lists custom, récurrence, rappels, templates, défauts. |
| 3 | `test_jalon3_calendar_boards.py` | Calendrier (vues, time-blocking, ICS), Kanban, Timeline, Eisenhower, vue annuelle/heatmap. |
| 4 | `test_jalon4_habits_focus_stats.py` | Habitudes, Focus, Countdown, page Summary, score/gamification, daily review. |
| 5 | `test_jalon5_sync_offline_data.py` | WebSocket sync, offline, pièces jointes + annotation, versions, export/import. |
| 6 | `test_jalon6_android.py` | Capacitor : gestes, widgets, Quick Ball, géofencing, Flip Start, strict mode (→ checklist). |
| 7 | `test_jalon7_windows.py` | Electron : hotkey global, tray, notifications natives, impression PDF (→ checklist). |
| 8 | `test_jalon8_polish.py` | Thèmes, fonds de liste, réglages, polish animations. |
| — | `test_scope_cuts.py` | Modules délibérément coupés (collab, notes, intégrations, captcha…). |
