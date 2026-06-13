# Modules 19 à 35

Critères d'acceptation testables ; `[J]` = jalon ; **COUPÉ** = hors périmètre (cf. README).

---

## Module 19 — Vues 8.0 & customisation
- `[J3]` **Vue annuelle + heatmap** : grille 12 mois ; matrice de densité (complétions +
  durée de focus) façon GitHub ; cliquer un jour ouvre l'aperçu des tâches complétées ;
  tap d'un jour = popover des tâches planifiées sans changer de vue.
- `[J8]` **Fonds de liste** : wallpaper/motif/couleur par liste.
- `[J3]` **Bascule calendrier moderne/classique** : grille classique vs cartes haute densité.
- **COUPÉ (19.3)** : AI-Suggested Tasks.

## Module 20 — Capture & extensions
- **COUPÉ (20.1)** : mailbox email-to-task.
- **COUPÉ (20.2)** : extension navigateur / web clipper.
- `[J2]` **(20.3) Résolution de lien tâche→tâche** : coller un deep link de tâche dans une
  description/sous-tâche le résout en bloc inline cliquable affichant titre + statut courant de la cible.

## Module 21 — Tracking avancé
- `[J4]` **(21.1) Multi-logs d'habitude** : plusieurs check-ins/jour ; plusieurs créneaux
  d'alarme distincts pour une même habitude.
- `[J4]` **(21.2) Estimation Pomodoro** : estimer un nombre de pomos sur une tâche ;
  analytics estimé vs réel (précision d'estimation).
- **COUPÉ (21.3 iOS)** : Live Activities / Dynamic Island. `[J6]` **Quick Ball Android** :
  bulle flottante (capture rapide, check-in d'habitude — **sans dictée vocale**).

## Module 22 — Focus strict & hooks physiques `[J6, Android]`
- **(22.1) Strict mode** : quitter l'app pendant une session annule le timer et **perd les
  données** de la session ; une **allowlist** d'apps (ex. Spotify) ne casse pas la session.
- **(22.2) Flip Start** : le timer ne tourne que téléphone **face contre table** ; le
  retourner/soulever met en pause automatiquement.

## Module 23 — Templates `[J2]`
- **(23.1)** Templates de **tâche** (checklist, notes, tags inclus) et de **liste/projet**
  (sections, sous-tâches, layout par défaut clonés) ; bibliothèque unifiée (lister/éditer/supprimer).
  **Templates de note coupés** (module 8 coupé).
- **(23.2)** `[J4]` Bibliothèque de presets d'habitudes (préremplit fréquence/icône/motto).

## Module 24 — Migration & backup `[J5]`
- **(24.1)** Importeur CSV générique (couvre Todoist/Microsoft To Do/Wunderlist/etc. via
  leur export CSV) ; `[J2]` **import copier-coller** : coller un bloc multi-lignes propose
  « 1 tâche/ligne » ou « 1 tâche unique ».
- **(24.2)** Backup zip (.csv : tâches actives/archivées, listes, priorités, descriptions) ;
  restore reconstruit la base.

## Module 25 — Comportements granulaires
- `[J1]` **(25.1) Progression** : pourcentage 0–100 (pas de 10) ; barre inline ; compléter force 100.
- `[J2]` **(25.2) Listes masquées** : `hidden_from_smart_lists` exclut les tâches des smart
  lists, sauf si la liste est explicitement ciblée en inclusion. (Déjà respecté par `?smart=1`.)
- `[J2]` **(25.3) Défauts de création** : liste/date/priorité/offset de rappel par défaut
  appliqués aux nouvelles tâches (`UserSettings.default_*`).

## Module 26 — Notifications & alertes
- `[J4]` **(26.1) Daily review** : cron (Celery beat) envoie un digest à une heure configurée
  (tâches du jour, habitudes, streak) ; carte de bilan hebdo.
- `[J2]` **(26.2) Snooze configurable** : options de snooze paramétrables (5/15 min, 1 h,
  demain matin, prochain jour ouvré) proposées quand une alerte sonne.

## Module 27 — Historique, impression, wearables
- `[J5]` **(27.1) Historique de versions** : ledger différentiel des éditions de la
  description ; parcourir l'historique et restaurer une version antérieure.
- `[J7]` **(27.2) Impression & export PDF** : listes, tâches, ou matrice d'Eisenhower ;
  options (inclure sous-tâches/commentaires, compact/étendu).
- **COUPÉ (27.3)** : Apple Watch / Wear OS.

## Module 28 — Règles partagées & modes d'habitude
- **COUPÉ (28.1)** : DND de liste partagée (mono-utilisateur).
- `[J4]` **(28.2) Modes de check-in d'habitude** : **auto** (tap = incrément préconfiguré),
  **manuel** (saisie de la quantité), **binaire** (simple coche).

## Module 29 — Interruptions de focus
- **COUPÉ (29.1)** : pause auto sur appel entrant.
- `[J4]` **(29.2) Timer dans l'onglet (web)** : le titre de l'onglet affiche le compte à
  rebours/temps écoulé pendant une session de focus (ex. `(24:12) TickTick | Focus`).

## Module 30 — Capture spatiale & contextuelle
- `[J6, mobile]` **(30.1) Plan Your Day** : icône en haut de « Today » ; file de triage des
  tâches en retard/non planifiées, une carte à la fois (compléter / reporter / supprimer) ;
  écran de succès en fin de file.
- `[J3]` **(30.2) Masquage de plages horaires** : masquer des heures inactives (ex. 00h–7h)
  dans les vues jour/semaine ; slider pour ajuster la plage visible.
- `[J6, mobile]` **(30.3) FAB (+) draggable** : long-press + drag du bouton d'ajout ;
  le drop ouvre la création à la position/section/parent ciblé.
- `[J1]` **(30.4) Entrée séquentielle de check items** : « Entrée » sauve l'item courant et
  ouvre la ligne suivante, curseur actif (saisie en chaîne sans re-cliquer « Ajouter »).

## Module 31 — Architecture des checklists `[J1]` (livré)
- **Tier 1 — sous-tâches** : objets `Task` à part entière (`parent`), datables/priorisables,
  planifiables au calendrier ; cocher toutes les sous-tâches termine le parent ;
  imbrication ≤ 5 niveaux.
- **Tier 2 — `CheckItem`** : tableau léger rattaché à la tâche ; pas de date/priorité propre ;
  réordonnable ; **cocher déplace l'item en bas** (auto-sort) avec horodatage.
- **Tier 3 — checkbox markdown** : `- [ ]` dans la description ; rendu cliquable côté front
  (`web/src/lib/markdown.ts`) ; aucune métadonnée en base.

## Module 32 — Annotation d'image `[J5]`
- Éditeur overlay à l'ouverture d'une image attachée : stylo (taille/couleur), formes
  (rectangle/cercle/flèche), texte.
- Sauver **aplatit** les calques et remplace le fichier en stockage (pas de ré-upload externe).

## Module 33 — Commentaires horodatés `[J1 base / J5 PJ]`
- `[J1]` Chaque commentaire a un timestamp serveur ; éditer **conserve `created_at`** et
  marque `edited_at` (indicateur « edited »). (Livré et testé.)
- `[J5]` Pièces jointes dans les commentaires (markdown/emoji).

## Module 34 — Intégrations avancées
- **COUPÉ ENTIER** : Notion two-way (34.1), Apple Health (34.2).

## Module 35 — Notes de countdown `[J4]`
- Fusionné dans le module 18 : chaque carte countdown porte une description riche (texte,
  idées, préparatifs).
