# Checklist d'acceptation manuelle — natif & UI lourde

Ce que la spec automatisée ne couvre pas : interactions natives (Android/Electron)
et UI fortement gestuelle. À vérifier **à la main** sur appareil/émulateur quand la
feature est livrée. Cocher `[x]` quand validé. Ajouter un smoke e2e (Playwright /
instrumentation) seulement si la régression devient coûteuse.

> Convention : chaque item porte son module PRD (`MNN`) pour la traçabilité.

## Web — UI lourde (Jalon 3 surtout)

### Calendrier (M4)
- [ ] M4 — Vues jour / 3 jours / semaine / mois / agenda affichent les bonnes tâches
- [ ] M4 — Section « all-day » séparée en haut des vues
- [ ] M4 — Drag d'une tâche non datée depuis la sidebar → planifiée à l'heure du drop
- [ ] M4 — Déplacer un bloc change la date/heure (et persiste après refresh)
- [ ] M16 — Tirer le bord bas d'un bloc change la durée
- [ ] M4 — Étirer une tâche sur plusieurs jours (mois/semaine) fixe une plage
- [ ] M30 — Masquage des heures inactives + slider d'ajustement
- [ ] M19 — Bascule calendrier moderne / classique

### Kanban (M5.1)
- [ ] M5 — Créer / renommer / supprimer / réordonner des colonnes
- [ ] M5 — Glisser une tâche entre colonnes (et réordonner dans une colonne)
- [ ] M5 — Replier une colonne
- [ ] M5 — Tri indépendant par colonne

### Timeline / Gantt (M5.2)
- [ ] M5 — Barres de tâches sur l'échelle jour/semaine/mois
- [ ] M5 — Tirer les bords change start/end ; déplacer la barre décale sans changer la durée
- [ ] M5 — Marqueur de jalon (durée nulle)

### Eisenhower (M13) & vue annuelle (M19)
- [ ] M13 — 4 quadrants + drag entre quadrants
- [ ] M19 — Heatmap annuelle + popover de jour

### Divers web
- [ ] M3 — Glisser une tâche sur un tag de la sidebar l'applique
- [ ] M2 — Réordonner listes / dossiers par drag
- [ ] M29 — Le titre de l'onglet affiche le compte à rebours pendant un focus
- [ ] M32 — Annotation d'image (stylo/formes/texte) puis sauvegarde aplatie

## Android — Capacitor (Jalon 6)

### Widgets (M11.1) — App Widgets natifs (Kotlin)
- [ ] M11 — Widget liste de tâches (Today / Inbox / custom) scrollable
- [ ] M11 — Widget Quick Add (barre de saisie)
- [ ] M11 — Widgets calendrier (mois / semaine / jour)
- [ ] M11 — Widget grille de check-in d'habitudes

### Gestes & système (M11.1, M30.3)
- [ ] M11 — Swipe gauche à double seuil : compléter / supprimer / déplacer
- [ ] M11 — Swipe droite : report rapide / changement de liste
- [ ] M11 — Notification persistante (shade) : tâches du jour + Quick Add
- [ ] M11 — Partage natif depuis une autre app préremplit le Quick Add
- [ ] M30 — FAB (+) draggable : drop ouvre la création à la position/section ciblée
- [ ] M30 — « Plan Your Day » : file de triage (compléter / reporter / supprimer)

### Capteurs & focus (M21.3, M22, M1)
- [ ] M21 — Quick Ball flottant (capture rapide, check-in — sans dictée)
- [ ] M22 — Strict mode : quitter l'app annule la session ; allowlist exempte certaines apps
- [ ] M22 — Flip Start : timer actif uniquement face contre table
- [ ] M1 — Rappel géolocalisé : déclenche à l'arrivée / au départ d'un rayon
- [ ] M11 — Notifications locales planifiées (rappels) avec actions

## Windows — Electron (Jalon 7)

- [ ] M11 — Hotkey global (ex. Ctrl+Alt+A) ouvre la mini-fenêtre de capture
- [ ] M11 — Tray : mini-liste de tâches + progression du timer de focus
- [ ] M11 — Lancement au démarrage, minimisé dans le tray
- [ ] M11 — Toasts natifs avec actions « Terminer » / « Snooze »
- [ ] M27 — Impression / export PDF (listes, tâches, matrice Eisenhower)
- [ ] M27 — Options de mise en page : sous-tâches / commentaires, compact / étendu
- [ ] Packaging NSIS (electron-builder) installe et lance sur Windows

## Transverse

- [ ] M12 — Sync temps réel : une action sur un client se reflète sur les autres
- [ ] M12 — Offline : créer/éditer hors-ligne, puis fusion à la reconnexion
- [ ] M26 — Daily review : notification du matin/soir à l'heure configurée
- [ ] M8 (thèmes) — Clair / sombre / auto + presets sur les 3 clients
