# Requirements — clone TickTick (source de vérité)

Ceci est le **PRD corrigé, complet et autonome**. Tout ce qu'il faut construire est
décrit ici : aucune information ne dépend d'une conversation externe. Un modèle qui
clone le dépôt doit pouvoir tout implémenter à partir de ces fichiers + des tests.

- [modules-01-12.md](modules-01-12.md) — modules 1 à 12 (cœur, listes, tags, calendrier, kanban, habitudes, focus, collab*, saisie/recherche, plateformes, compte/sync).
- [modules-13-18.md](modules-13-18.md) — modules 13 à 18 (absents du PRD d'origine, comblés : Eisenhower, Won't Do, Annoying Alert, durée, Summary, Countdown).
- [modules-19-35.md](modules-19-35.md) — modules 19 à 35 (vues 8.0, capture, tracking avancé, focus strict, templates, migration, comportements granulaires, notifications, historique/print, règles habitudes, interruptions focus, capture spatiale, checklists, annotation image, commentaires, intégrations*, countdown notes).

`*` partiellement ou totalement coupé — voir « Décisions globales » ci-dessous.

## Comment lire un module

Chaque module liste des **exigences sous forme de critères d'acceptation testables**
(« quand X, alors Y »). Chaque exigence est rattachée à un **jalon** et à son
**emplacement de test**. La règle : implémenter = rendre le test correspondant vert
(cf. [../test-strategy.md](../test-strategy.md) et [../../CLAUDE.md](../../CLAUDE.md)).

## Décisions globales (baked-in, non négociables)

### Périmètre
- **Mono-utilisateur.** Aucune collaboration : le **module 9 entier** est coupé
  (partage, rôles, assignation, @mentions, flux collaboratif, « Assigned to me »,
  DND de liste partagée 28.1, critère de filtre « assignee »).
- **Coupé à la demande de l'utilisateur** : **module 8 (Notes) entier** ; saisie /
  dictée vocale ; pause auto du focus sur appel entrant (29.1) ; **tout captcha,
  rate-limiting et vérification d'email** (système ouvert pour développeurs).
- **Intégrations externes coupées** : OAuth Google/Outlook bidirectionnel & CalDAV
  (4.3), email-to-task (20.1), suggestions IA (19.3), Notion (34.1), Apple Health
  (34.2). **Seul l'abonnement ICS en lecture seule est conservé.**
- **Hors périmètre client** (web / Android / Windows uniquement) : web clipper (20.2),
  wearables (27.3), iOS / macOS / Linux, Live Activities / Dynamic Island.
- **Hallucinations du PRD retirées** : Task Merging (1.2), sticky notes desktop (11.2),
  Shake to Clean (11.1), rappels par email par tâche.

### Corrections factuelles
- Priorités : `0` none (gris), `1` low (bleu), `3` medium (**jaune**), `5` high (rouge).
- Imbrication des sous-tâches **plafonnée à 5 niveaux**.
- Countdown (35/18) = fonctionnalité Dida365 ; implémentée quand même, en simple.

### Valeurs canoniques (à respecter partout)
- `Task.status` : `0` normal, `2` completed, `-1` wont_do.
- `Task.priority` : `0 / 1 / 3 / 5`.
- Corbeille : soft-delete **30 jours** ; 1er delete → corbeille, 2e (ou `?permanent=1`) → définitif.
- **3 tiers de checklist** : Tier 1 = sous-tâche (`Task.parent`, datable, ≤5 niveaux) ;
  Tier 2 = `CheckItem` (léger, auto-trié en bas si coché) ; Tier 3 = checkbox markdown (front).
- **Smart lists** = pas d'endpoint dédié ; composées via query params sur `/api/tasks/`.

## Carte module → jalon → spec

| Module(s) | Jalon | Spec |
|-----------|-------|------|
| 1, 2.1–2.2, 3 (plat), 10, 14, 25.1, 31, 33 | 1 | `backend/spec/test_jalon1_acceptance.py` (réels) |
| 2.1 dossiers/perso, 2.3 filtres, 3 nested, 1 récurrence/rappels, 15, 23, 24.1, 25.3, 26.2, 20.3 | 2 | `backend/spec/test_jalon2_organization.py` |
| 4, 5, 13, 16, 19.1–19.2, 30.2 | 3 | `backend/spec/test_jalon3_calendar_boards.py` |
| 6, 7, 17, 18, 12.3, 26.1, 21, 28.2, 29.2, 35 | 4 | `backend/spec/test_jalon4_habits_focus_stats.py` |
| 12.1, 24, 1.1 (PJ), 32, 27.1, 10.2 (avancé) | 5 | `backend/spec/test_jalon5_sync_offline_data.py` |
| 11.1, 21.3, 22, 30.1, 30.3, 1.1 (géo) | 6 | `backend/spec/test_jalon6_android.py` + checklist |
| 11.2, 27.2 | 7 | `backend/spec/test_jalon7_windows.py` + checklist |
| 12.2, 19.2 (fonds) | 8 | `backend/spec/test_jalon8_polish.py` |
| Tout le périmètre coupé | — | `backend/spec/test_scope_cuts.py` |
