# Modules 1 à 12

Format : exigences en critères d'acceptation testables. `[J1]` = jalon. Les
décisions globales (cuts, valeurs canoniques) sont dans [README.md](README.md).

---

## Module 1 — Moteur de tâches

### 1.1 Propriétés
- `[J1]` Titre texte (unicode/emoji) ; description multi-lignes markdown.
- `[J1]` Priorité none/low/medium/high (0/1/3/5) ; tri par priorité décroissante.
- `[J1]` Date+heure d'échéance, date+heure de début, flag `is_all_day`, fuseau propre à la tâche.
- `[J1]` Sous-tâches : 3 tiers (cf. module 31). Tier 1 imbriqué ≤ 5 niveaux ; un Tier 1
  peut hériter ou avoir ses propres date/priorité ; convertir un check item (Tier 2) en tâche (Tier 1).
- `[J2]` **Récurrence (RRULE RFC 5545)** : presets quotidien/hebdo/mensuel/annuel ;
  custom « tous les X » ; jours précis (BYDAY) ; relatif (premier lundi, dernier jour,
  jour ouvré) ; **après complétion** (`repeat_from=completion`) ; fin = jamais / date
  (UNTIL) / N occurrences (COUNT). Compléter **avance la date** (pas de duplication).
- `[J2]` **Rappels** : jusqu'à 5/tâche ; relatifs (à l'heure due, 5/30 min, 1 h, 1 j avant,
  custom) ou absolus (date+heure). Livraison push + notification système. **Pas d'email.**
- `[J6]` **Rappels géolocalisés** : rayon autour d'un lieu, déclenche à l'arrivée ou au départ (Android).
- `[J5]` **Pièces jointes** : fichiers, images (preview), note vocale (enregistrement audio simple, sans transcript).
- `[J1/J2]` **Journal d'activité** : consigne création, changements de date, complétion.
- `[J1]` **Commentaires** : section horodatée (cf. module 33).

### 1.2 Actions
- `[J1]` Compléter / rouvrir ; **Won't Do** (cf. module 14).
- `[J1]` Report rapide : Demain, Semaine prochaine, +1 j, +3 j (conserve l'heure si présente).
- `[J1]` Épingler en haut de liste (`is_pinned` + `pinned_at` pour l'ordre).
- `[J1]` Dupliquer (avec ou sans sous-tâches/PJ).
- `[J1]` Deep link `app://task/:id` (natif) / `/task/:id` (web).
- `[J5]` Archiver les tâches terminées (alléger les vues actives).
- `[J1]` Corbeille soft-delete 30 j + vidage.
- **COUPÉ** : Task Merging (fusion de plusieurs tâches).

---

## Module 2 — Listes, dossiers, smart lists

### 2.1 Organisation `[J1 base / J2 avancé]`
- `[J1]` **Inbox** : liste par défaut, **non supprimable, non renommable** (autres réglages OK).
- `[J1]` Listes custom : créer, renommer, supprimer.
- `[J2]` **Dossiers** (ProjectGroup) : regrouper des listes, repliables, drag in/out.
- `[J2]` Personnalisation : couleur (palette 30+), emoji/icône preset, vue par défaut
  (list/kanban/timeline), archivage de liste.

### 2.2 Smart lists par défaut `[J1]`
Composées via query params sur `/api/tasks/` (cf. `test_jalon1_acceptance.py`) :
- Today : dues aujourd'hui **ou** en retard, non terminées.
- Tomorrow ; Next 7 Days ; All (agrégé) ; Inbox ; Completed (plat, groupé par `completed_at`).
- **COUPÉ** : « Assigned to me » (mono-utilisateur).

### 2.3 Smart lists custom `[J2]`
- Constructeur booléen AND/OR imbriqué.
- Critères : plage de dates (absolue / relative « dans X j » / en retard / sans date) ;
  listes/dossiers (inclure/exclure) ; tags (un / tous / exclure) ; priorité (= / > / <) ;
  statut (terminé / non terminé). **Critère assignee coupé.**
- Groupement + tri sauvegardés par smart list.

---

## Module 3 — Tags
- `[J1]` Tags plats : créer (le `#` est normalisé), assigner, filtrer les tâches par tag, couleur.
- `[J2]` Hiérarchie (`#Work/Marketing` via `parent`) ; renommage propagé globalement
  (référence par id) ; **merge** (re-tague les tâches, reparente les enfants) ;
  drag d'une tâche sur un tag de la sidebar pour l'appliquer.

---

## Module 4 — Calendrier & scheduling `[J3]`
- Vues jour / 3 jours / semaine (grille horaire) / mois / agenda ; section all-day.
- Tâche récurrente projetée en occurrences à la volée sur la plage.
- Time-blocking : drag d'une tâche non datée → start+due ; déplacer un bloc change les
  dates ; resize du bord bas change la durée ; étirer multi-jours fixe une plage.
- **Abonnement ICS en lecture seule** : importer une URL .ics, afficher/masquer ses événements.
- **COUPÉ** : OAuth Google/Outlook bidirectionnel, CalDAV.

---

## Module 5 — Kanban & Timeline `[J3]`
### 5.1 Kanban
- Sections (colonnes) : créer/renommer/supprimer/réordonner ; bouton « Add Section ».
- Drag d'une tâche entre colonnes (maj `section` + `sort_order`) ; tri indépendant par
  colonne (date/priorité/titre/manuel) ; replier une colonne (`collapsed`).
### 5.2 Timeline (Gantt)
- Tâches en barres sur échelle jour/semaine/mois ; tirer les bords change start/end ;
  déplacer la barre décale sans changer la durée ; tâche de durée nulle = jalon.

---

## Module 6 — Habit tracker `[J4]`
- Habitude : nom, emoji/icône, couleur.
- Fréquence : quotidien, hebdo, jours précis, intervalle (« tous les 3 j »), objectif
  hebdo (« 3×/semaine »).
- Objectif : binaire (oui/non) ou numérique avec unité custom (« 8000 pas », « 2000 ml »).
- Rappels d'habitude indépendants des tâches ; motto optionnel au check-in.
- Check-in en un tap ; note de réflexion optionnelle.
- Vue calendrier mensuelle (jours complets/partiels, streak courant/max) ; analytics
  (taux de complétion, comparaisons, paliers).
- Bibliothèque de presets (préremplit fréquence/icône/motto) — cf. module 23.2.
- 3 modes de check-in et multi-logs : cf. modules 28.2 et 21.1.

---

## Module 7 — Focus & time-tracking `[J4]`
### 7.1 Timer
- Pomodoro : durées travail/break court/long personnalisables, intervalle de break long,
  auto-start de la session suivante. Chronomètre count-up.
- Tâche associée : le temps est logué sur cette tâche. Estimation pomo : cf. module 21.2.
- Sons d'ambiance mixables (pluie, forêt, café, vagues, horloge, bruit blanc) + volume.
- Mode plein écran sans distraction ; (mobile) verrouillage d'orientation.
### 7.2 Statistiques
- Chaque session enregistre début/fin/durée/tâche.
- Répartition par liste/tag (camembert) ; tendances jour/semaine/mois ; streaks de focus.

---

## Module 8 — Notes & markdown
**COUPÉ ENTIER** (demande utilisateur). Pas de bascule tâche↔note, outliner, templates
de notes, `kind=NOTE`. Les descriptions markdown riches des tâches restent (avec
checkboxes Tier 3 et historique de versions sur la description — module 27.1).

---

## Module 9 — Collaboration
**COUPÉ ENTIER** (mono-utilisateur) : partage de listes, rôles Owner/Member/Viewer,
assignation, flux d'activité collaboratif, @mentions, DND de liste partagée (28.1).

---

## Module 10 — Saisie & recherche
### 10.1 NLP de saisie rapide `[J1]` (logique pure web, déjà livrée et testée)
- `tomorrow at 1pm` → date+heure ; `!high`/`!!!` → priorité ; `#tag` → tag ;
  `^Liste`/`~Liste` → liste. Toggle strip/keep du texte parsé ; toggle on/off par saisie.
  Implémentation : `web/src/lib/nlp.ts`, tests `web/src/lib/__tests__/nlp.test.ts`.
### 10.2 Recherche
- `[J1]` Recherche instantanée titres + descriptions + check items (`?q=`).
- `[J5]` Filtres avancés (liste, tag, date, statut, présence de PJ) ; historique des recherches.

---

## Module 11 — Plateformes
### 11.1 Android `[J6]`
- Widgets : liste de tâches scrollable, Quick Add, calendrier (mois/semaine/jour),
  grille de check-in d'habitudes (App Widgets natifs Kotlin).
- Notification persistante (shade) : tâches du jour + Quick Add.
- Gestes : swipe gauche à double seuil (compléter/supprimer/déplacer), swipe droite
  (report rapide / changer de liste).
- Partage natif depuis une autre app → préremplit le Quick Add.
- **COUPÉ** : Siri/Assistant, Shake to Clean, dictée vocale.
### 11.2 Windows `[J7]`
- Hotkey global (ex. Ctrl+Alt+A) → mini-fenêtre de capture flottante.
- Tray : mini-liste + progression du timer ; lancement minimisé au démarrage ;
  toasts natifs avec actions Terminer / Snooze.
- **COUPÉ** : sticky notes desktop, client Linux/macOS.

---

## Module 12 — Compte, sync, gamification
### 12.1 Sync & offline `[J5]`
- WebSocket (Channels) : une mutation est diffusée aux autres connexions du même user ;
  `seq` croissant par user ; auth WebSocket via JWT.
- Offline : mutations en file locale (IndexedDB web/Electron, SQLite Capacitor) avec UUID
  client (idempotent), rejouées à la reconnexion ; conflit = last-write-wins par champ.
- Export/import CSV & JSON (cf. module 24).
### 12.2 Réglages `[J1 base / J8 thèmes]`
- Thèmes clair/sombre/auto + presets (Lavender, Forest…). Sons de rappel. Début de
  semaine (dim/lun/sam). Visibilité des smart lists par défaut. Défauts de création (25.3).
### 12.3 Gamification `[J4]`
- Score de productivité quotidien (+ complétion à l'heure/streaks, − retards/overdue).
- Niveaux & badges (heures de focus + complétions cumulées) ; cartes de bilan quotidien/hebdo (26.1).
