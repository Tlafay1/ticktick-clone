"""Jalon 4 — Habitudes, Focus, Countdown, Statistiques (stubs).

Modules PRD : 6 (habitudes), 7 (focus), 18/35 (countdown), 17 (summary),
12.3 (gamification), 26.1 (daily review), 21 (multi-log, pomo estimation),
28.2 (modes de check-in), 29.2 (timer dans l'onglet web).
"""
import pytest

pytestmark = pytest.mark.spec
TODO = NotImplementedError


class TestM06HabitConfig:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Configuration d'habitude")

    def test_name_icon_color(self):
        """Habitude : nom, emoji/icône, couleur."""
        raise TODO

    def test_frequency_daily_weekly_specific_days_interval_goalcount(self):
        """Fréquence : quotidien, hebdo, jours précis, « tous les 3 jours », « 3×/semaine »."""
        raise TODO

    def test_goal_binary_or_numeric_with_unit(self):
        """Objectif binaire (oui/non) ou numérique avec unité (« 8000 pas »)."""
        raise TODO

    def test_habit_reminders_independent_of_tasks(self):
        """Rappels d'habitude indépendants des rappels de tâche."""
        raise TODO

    def test_optional_motto(self):
        """Encouragement/motto optionnel affiché au check-in."""
        raise TODO


class TestM28HabitCheckInModes:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Modes de check-in")

    def test_automatic_increment_mode(self):
        """Mode auto : un tap logue l'incrément préconfiguré (ex. « 1 verre »)."""
        raise TODO

    def test_manual_entry_mode_prompts_quantity(self):
        """Mode manuel : le check-in demande la quantité exacte."""
        raise TODO

    def test_binary_complete_all_mode(self):
        """Mode binaire : simple coche oui/non."""
        raise TODO


class TestM21HabitMultiLog:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Multi-check-ins & créneaux")

    def test_multiple_checkins_per_day(self):
        """Plusieurs check-ins/jour (« boire 5× »)."""
        raise TODO

    def test_multiple_time_slot_alarms(self):
        """Plusieurs créneaux d'alarme pour une même habitude (10h, 18h, 23h)."""
        raise TODO


class TestM06HabitTrackingStats:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Suivi & stats d'habitude")

    def test_one_tap_checkin_from_sidebar(self):
        """Check-in en un tap depuis la sidebar/widget."""
        raise TODO

    def test_daily_reflection_note(self):
        """Note de réflexion optionnelle attachée à un check-in."""
        raise TODO

    def test_streak_calendar_current_and_max(self):
        """Vue calendrier mensuelle : jours complets/partiels, streak courant/max."""
        raise TODO

    def test_completion_rate_graphs(self):
        """Graphes : taux de complétion, comparaisons, paliers de streak."""
        raise TODO

    def test_preset_library_autoconfigures(self):
        """La bibliothèque de presets préremplit fréquence/icône/motto."""
        raise TODO


class TestM07Focus:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Focus (Pomodoro/chrono)")

    def test_pomodoro_custom_durations_and_long_break_interval(self):
        """Travail/break courts/longs personnalisables + intervalle de break long."""
        raise TODO

    def test_auto_start_next_session(self):
        """Option d'enchaînement automatique des sessions."""
        raise TODO

    def test_stopwatch_count_up(self):
        """Mode chronomètre (count-up)."""
        raise TODO

    def test_session_logged_to_associated_task(self):
        """Le temps d'une session est attribué à la tâche sélectionnée."""
        raise TODO

    def test_ambient_sounds_mix_and_volume(self):
        """Sons d'ambiance (pluie, forêt…) mixables avec volume."""
        raise TODO


class TestM21FocusEstimation:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Estimation Pomodoro")

    def test_estimated_pomos_on_task(self):
        """Estimer un nombre de pomodoros sur une tâche."""
        raise TODO

    def test_actual_vs_estimated_accuracy(self):
        """Comparer focus estimé vs réel (précision d'estimation)."""
        raise TODO


class TestM07FocusStats:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Statistiques de focus")

    def test_focus_logs_persisted(self):
        """Chaque session enregistre début/fin/durée/tâche."""
        raise TODO

    def test_distribution_by_list_tag_pie(self):
        """Répartition du focus par liste/tag (camembert)."""
        raise TODO

    def test_trends_and_streaks(self):
        """Tendances (jour/semaine/mois) et streaks de focus."""
        raise TODO


class TestM29WebTabTimer:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Timer dans l'onglet (web)")

    def test_tab_title_shows_running_countdown(self):
        """Le titre de l'onglet affiche le compte à rebours pendant le focus."""
        raise TODO


class TestM18Countdown:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Countdown")

    def test_countdown_card_shows_days_remaining(self):
        """Carte countdown : jours restants jusqu'à une date (anniv./échéance)."""
        raise TODO

    def test_countdown_pinned_and_rich_note(self):
        """Countdown épinglable avec description riche (M35)."""
        raise TODO


class TestM17Summary:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Page Summary/statistiques")

    def test_today_score_completed_overdue(self):
        """Vue d'ensemble : score du jour, tâches complétées/en retard."""
        raise TODO

    def test_distribution_by_list_and_best_hours(self):
        """Distribution par liste, meilleures heures de productivité."""
        raise TODO

    def test_monthly_history(self):
        """Historique mensuel agrégé."""
        raise TODO


class TestM12Gamification:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Score & gamification")

    def test_productivity_score_daily_adjustments(self):
        """Score quotidien : + complétion à l'heure/streaks, − retards/overdue."""
        raise TODO

    def test_levels_and_badges(self):
        """Niveaux/badges selon heures de focus et complétions cumulées."""
        raise TODO


class TestM26DailyReview:
    pytestmark = pytest.mark.skip(reason="Jalon 4 — Daily review (Celery beat)")

    def test_morning_or_evening_digest_dispatched(self):
        """Un digest est envoyé à l'heure configurée (tâches du jour, habitudes, streak)."""
        raise TODO

    def test_weekly_summary_card(self):
        """Carte de bilan hebdo (complétions, focus, progression)."""
        raise TODO
