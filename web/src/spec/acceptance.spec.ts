/**
 * Carte d'acceptation FRONT (web) — spec vivante.
 *
 * `it.todo(...)` = comportement UI planifié (jaune dans vitest, jamais faux
 * positif). La logique pure déjà livrée a ses tests réels ailleurs :
 *   - NLP de saisie rapide  → src/lib/__tests__/nlp.test.ts          (Jalon 1 ✓)
 *   - Checkboxes markdown   → src/lib/__tests__/markdown.test.ts     (Jalon 1 ✓)
 *   - Dates/labels/report   → src/lib/__tests__/dates.test.ts        (Jalon 1 ✓)
 *
 * Quand on livre un comportement, on remplace son `it.todo` par un vrai test
 * (Vue Test Utils pour les composants, ou test de store/logique pure).
 * Le natif et l'UI lourde sont dans docs/acceptance-checklist.md.
 */
import { describe, it } from 'vitest'

// ---------------------------------------------------------------------------
describe('Jalon 1 — cœur web (composants à brancher sur l\'API déjà prête)', () => {
  it.todo('M2 — la sidebar liste smart lists par défaut + listes + Inbox épinglée')
  it.todo('M2 — sélectionner une smart list charge les tâches via les bons query params')
  it.todo('M1 — la quick-add applique le parseur NLP et crée la tâche (strip/keep selon settings)')
  it.todo('M1 — cocher une tâche appelle complete/ et l\'anime hors de la liste')
  it.todo('M14 — clic droit / appui long sur la checkbox propose « Won\'t Do »')
  it.todo('M1 — le panneau de détail édite titre, description markdown, dates, priorité, tags')
  it.todo('M31 — Tier 2 : entrée séquentielle de check items (Enter crée la ligne suivante)')
  it.todo('M31 — Tier 3 : cliquer une checkbox markdown bascule le texte et sauvegarde')
  it.todo('M1 — menu d\'actions : épingler, dupliquer, reporter (Tomorrow/Next week/+1j/+3j)')
  it.todo('M2 — la corbeille liste les tâches supprimées et permet restore / vider')
  it.todo('M10 — la recherche globale filtre titres/descriptions/check items en direct')
  it.todo('Deep link : ouvrir app://task/:id (et /task/:id sur web) focalise la tâche')
})

describe('Jalon 2 — organisation', () => {
  it.todo('M2 — drag & drop : réordonner listes, entrer/sortir d\'un dossier')
  it.todo('M2 — éditeur de liste : couleur (palette 30+), emoji/icône, vue par défaut, archive')
  it.todo('M2 — constructeur de smart list custom (groupes AND/OR, tous les critères)')
  it.todo('M3 — tags hiérarchiques dans la sidebar, couleurs, merge par drag, drag tâche→tag')
  it.todo('M1 — éditeur de récurrence (presets + custom + après complétion + fin)')
  it.todo('M1/M15 — éditeur de rappels multiples (≤5) + bascule Annoying Alert')
  it.todo('M26 — quand une alerte sonne, propose les options de snooze configurées')
  it.todo('M23 — enregistrer/insérer un template de tâche et de liste')
  it.todo('M24 — coller un bloc multi-lignes propose 1 tâche/ligne ou 1 tâche')
  it.todo('M20 — un deep link collé dans une description se résout en bloc inline cliquable')
})

describe('Jalon 3 — calendrier, kanban, timeline, eisenhower', () => {
  it.todo('M4 — vues jour/3 jours/semaine/mois/agenda + section all-day')
  it.todo('M4 — drag-to-schedule depuis la sidebar, resize de durée, multi-jours (checklist)')
  it.todo('M30 — masquage de plages horaires avec slider')
  it.todo('M5 — board Kanban : colonnes CRUD/réordonner/replier, DnD entre colonnes')
  it.todo('M5 — Timeline/Gantt : barres, resize des bords, déplacement, jalons')
  it.todo('M13 — matrice d\'Eisenhower : 4 quadrants, DnD entre quadrants')
  it.todo('M19 — vue annuelle + heatmap de productivité, popover de jour')
})

describe('Jalon 4 — habitudes, focus, countdown, stats', () => {
  it.todo('M6 — création d\'habitude (fréquence, objectif numérique+unité, presets)')
  it.todo('M28 — 3 modes de check-in : auto / saisie manuelle / binaire')
  it.todo('M6 — vue streak calendrier + graphes d\'analytics')
  it.todo('M7 — timer focus Pomodoro/chrono, sons d\'ambiance, tâche associée')
  it.todo('M29 — le titre de l\'onglet affiche le compte à rebours du focus')
  it.todo('M17 — page Summary (score, complétées/en retard, distribution, meilleures heures)')
  it.todo('M18 — cartes countdown avec jours restants et description riche')
})

describe('Jalon 5 — sync, offline, données', () => {
  it.todo('M12 — couche offline : IndexedDB + file de mutations rejouée à la reconnexion')
  it.todo('M12 — WebSocket : une mutation distante met à jour l\'UI en direct')
  it.todo('M1 — pièces jointes : upload fichier/image, note vocale (enregistrement audio)')
  it.todo('M32 — éditeur d\'annotation d\'image (stylo/formes/texte) sur canvas')
  it.todo('M27 — historique de versions de la description + restauration')
  it.todo('M12/M24 — export/import CSV & JSON, importeur CSV générique')
})

describe('Jalon 8 — finitions', () => {
  it.todo('M12 — moteur de thèmes clair/sombre/auto + presets de couleurs')
  it.todo('M19 — fond personnalisé par liste')
  it.todo('M12 — réglages : début de semaine, visibilité des smart lists, son de rappel')
})
