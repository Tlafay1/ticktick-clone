# Modules 13 à 18 (comblés)

Le PRD d'origine sautait de 12 à 19. Ces modules sont les **vraies fonctionnalités
TickTick** absentes du PRD, ajoutées pour compléter le périmètre. Critères d'acceptation
testables ; `[J]` = jalon.

---

## Module 13 — Matrice d'Eisenhower `[J3]`
- Vue à 4 quadrants : Urgent×Important, Important non urgent, Urgent non important, ni l'un ni l'autre.
- Critères de quadrant **configurables** (par priorité, par date d'échéance, par tag).
- Drag-and-drop d'une tâche entre quadrants → ajuste les champs sous-jacents (priorité/date/tag).
- Imprimable (cf. module 27.2).

---

## Module 14 — Statut « Won't Do » `[J1]` (livré)
- 3ᵉ état de complétion : `status = -1` (abandonné), distinct de terminé (`2`).
- Accessible par clic droit / appui long sur la checkbox.
- Une tâche Won't Do : `completed_at` renseigné ; **n'apparaît ni dans les actives ni dans
  les terminées** ; filtrable via `?status=-1`.
- Rendu visuel : titre barré différemment de « terminé ».

---

## Module 15 — Annoying Alert `[J2]`
- Option **par rappel** : alerte persistante/répétitive plein écran qui sonne jusqu'à
  interaction explicite de l'utilisateur (par opposition à une notification one-shot).
- Réutilise le système de rappels du module 1.1 (un flag `annoying` sur le rappel).

---

## Module 16 — Durée & heure de fin `[J3]`
- Une tâche peut porter date+heure de **début** ET de **fin** (donc une durée).
- Dans les vues calendrier, elle s'affiche comme **bloc** couvrant sa durée.
- Le resize du bord bas d'un bloc (module 4.2) modifie cette durée.
- Les champs existent déjà (`start_date` / `due_date` / `is_all_day` sur `Task`).

---

## Module 17 — Page Summary / Statistiques `[J4]`
- Vue d'ensemble : score du jour, nombre de tâches complétées et en retard.
- Distribution des tâches par liste ; meilleures heures de productivité.
- Historique mensuel agrégé.
- S'appuie sur le journal d'activité (module 1.1) et les sessions de focus (module 7.2).

---

## Module 18 — Countdown (jours restants) `[J4]`
- Cartes « compte à rebours » (anniversaires, échéances, jalons) affichant le **nombre de
  jours restants** jusqu'à une date.
- Épinglables ; chaque carte porte une **description riche** (idées cadeaux, préparatifs,
  notes) — couvre le module 35.
- Entité dédiée `Countdown` (distincte de `Task`).
