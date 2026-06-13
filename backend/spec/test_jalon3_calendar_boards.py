"""Jalon 3 — Calendrier, Kanban, Timeline, Eisenhower (stubs).

Modules PRD : 4 (calendrier & scheduling), 5 (kanban & timeline), 13 (Eisenhower),
16 (durée), 19.1 (vue annuelle + heatmap), 19.2 (calendrier moderne/classique),
30.2 (masquage de plages horaires).
La manipulation directe (drag-to-schedule, resize, DnD) est vérifiée par la
checklist manuelle ; ici on couvre les contrats backend/données.
"""
import pytest

pytestmark = pytest.mark.spec
TODO = NotImplementedError


class TestM04CalendarViews:
    pytestmark = pytest.mark.skip(reason="Jalon 3 — Vues calendrier")

    def test_tasks_in_range_for_day_3day_week_month_agenda(self):
        """L'API renvoie les tâches datées d'une plage [start, end] pour alimenter
        les vues jour/3 jours/semaine/mois/agenda."""
        raise TODO

    def test_all_day_section_separates_timeless_tasks(self):
        """Les tâches `is_all_day` remontent dans la section all-day."""
        raise TODO

    def test_recurring_task_projected_as_multiple_occurrences(self):
        """Une tâche récurrente est projetée en occurrences à la volée sur la plage."""
        raise TODO


class TestM04TimeBlocking:
    pytestmark = pytest.mark.skip(reason="Jalon 3 — Time-blocking (drag/resize)")

    def test_drag_undated_task_sets_start_due(self):
        """Glisser une tâche non datée sur le calendrier fixe start+due."""
        raise TODO

    def test_reschedule_changes_dates(self):
        """Déplacer un bloc change ses dates/heures."""
        raise TODO

    def test_resize_changes_duration(self):
        """Redimensionner le bas d'un bloc allonge/raccourcit la durée (M16)."""
        raise TODO

    def test_multiday_drag_sets_start_end_range(self):
        """Étirer sur plusieurs jours fixe une plage start..due."""
        raise TODO


class TestM16Duration:
    pytestmark = pytest.mark.skip(reason="Jalon 3 — Durée & heure de fin")

    def test_task_with_start_and_due_renders_as_block(self):
        """start_date + due_date (même jour, heures distinctes) = bloc daté avec durée."""
        raise TODO


class TestM04IcsSubscription:
    pytestmark = pytest.mark.skip(reason="Jalon 3 — Abonnement ICS lecture seule")

    def test_subscribe_ics_url_parses_events(self):
        """Abonner une URL .ics importe ses événements en lecture seule."""
        raise TODO

    def test_external_events_toggle_visibility(self):
        """On peut afficher/masquer les événements d'un calendrier externe."""
        raise TODO


class TestM05Kanban:
    pytestmark = pytest.mark.skip(reason="Jalon 3 — Kanban")

    def test_section_crud_and_reorder(self):
        """Sections : créer/renommer/supprimer/réordonner (cf. modèle Section)."""
        raise TODO

    def test_move_task_between_sections(self):
        """Déplacer une tâche entre colonnes met à jour `section` et `sort_order`."""
        raise TODO

    def test_per_column_sort_rule(self):
        """Chaque colonne trie indépendamment (date/priorité/titre/manuel)."""
        raise TODO

    def test_collapse_column(self):
        """Replier une section persiste `collapsed`."""
        raise TODO


class TestM05Timeline:
    pytestmark = pytest.mark.skip(reason="Jalon 3 — Timeline/Gantt")

    def test_tasks_render_as_bars_on_scale(self):
        """Les tâches datées s'affichent en barres (échelle jour/semaine/mois)."""
        raise TODO

    def test_drag_edges_change_start_end(self):
        """Tirer les bords d'une barre change start/end."""
        raise TODO

    def test_drag_bar_moves_without_changing_duration(self):
        """Déplacer la barre décale la plage sans changer la durée."""
        raise TODO

    def test_zero_duration_milestone(self):
        """Une tâche de durée nulle = marqueur jalon."""
        raise TODO


class TestM13Eisenhower:
    pytestmark = pytest.mark.skip(reason="Jalon 3 — Matrice d'Eisenhower")

    def test_four_quadrants_by_configurable_criteria(self):
        """4 quadrants (urgent×important) selon des critères configurables (priorité/date/tag)."""
        raise TODO

    def test_drag_between_quadrants_updates_task(self):
        """Glisser une tâche entre quadrants ajuste les champs sous-jacents."""
        raise TODO


class TestM19YearViewHeatmap:
    pytestmark = pytest.mark.skip(reason="Jalon 3 — Vue annuelle & heatmap")

    def test_year_grid_completion_density(self):
        """Grille 12 mois : densité de complétion + durée de focus par jour (heatmap)."""
        raise TODO

    def test_click_day_shows_completed_tasks_popover(self):
        """Cliquer un jour ouvre l'aperçu des tâches complétées ce jour-là."""
        raise TODO


class TestM19ModernClassicCalendar:
    pytestmark = pytest.mark.skip(reason="Jalon 3 — Bascule calendrier moderne/classique")

    def test_toggle_layout_persists(self):
        """La bascule grille classique / cartes modernes est mémorisée."""
        raise TODO


class TestM30TimelineSlotHiding:
    pytestmark = pytest.mark.skip(reason="Jalon 3 — Masquage de plages horaires")

    def test_hide_inactive_hours_with_slider(self):
        """Masquer des heures (ex. 00h–7h) ; un slider ajuste la plage visible."""
        raise TODO
