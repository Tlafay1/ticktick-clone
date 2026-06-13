"""Jalon 6 — Client Android / Capacitor (stubs).

Modules PRD : 11.1 (widgets, gestes, notif shade, share sheet), 21.3 (Quick Ball),
22 (strict mode, Flip Start), 30.1 (Plan Your Day), 30.3 (FAB draggable),
1.1 (rappels géolocalisés).

La plupart de ces comportements sont natifs/UI → vérifiés par la checklist
manuelle (`docs/acceptance-checklist.md`). Les stubs ci-dessous tracent les
contrats côté données/API que le client mobile consomme. Saisie vocale : COUPÉE.
"""
import pytest

pytestmark = pytest.mark.spec
TODO = NotImplementedError


class TestM11AndroidWidgets:
    pytestmark = pytest.mark.skip(reason="Jalon 6 — Widgets Android (checklist manuelle)")

    def test_task_list_widget_feed(self):
        """L'API fournit un flux de tâches (Today/Inbox/custom) pour le widget liste."""
        raise TODO

    def test_quick_add_widget_creates_task(self):
        """Le widget Quick Add crée une tâche depuis une barre de texte."""
        raise TODO

    def test_calendar_and_habit_widgets_data(self):
        """Données pour widgets calendrier (mois/semaine/jour) et grille d'habitudes."""
        raise TODO


class TestM11AndroidGestures:
    pytestmark = pytest.mark.skip(reason="Jalon 6 — Gestes & shade (checklist manuelle)")

    def test_left_swipe_thresholds(self):
        """Swipe gauche à double seuil : compléter/supprimer/déplacer selon distance."""
        raise TODO

    def test_right_swipe_quick_postpone(self):
        """Swipe droite : report rapide ou changement de liste."""
        raise TODO

    def test_persistent_notification_shade(self):
        """Notification persistante : tâches du jour + raccourci Quick Add."""
        raise TODO

    def test_native_share_to_app_prefills_quickadd(self):
        """Partage natif depuis une autre app préremplit le Quick Add (texte/URL)."""
        raise TODO


class TestM30MobileWorkflows:
    pytestmark = pytest.mark.skip(reason="Jalon 6 — Plan Your Day & FAB (checklist manuelle)")

    def test_plan_your_day_triage_queue(self):
        """« Plan Your Day » : file de triage des tâches en retard/non planifiées."""
        raise TODO

    def test_draggable_fab_contextual_insert(self):
        """Le FAB (+) draggable ouvre la création à la position/section ciblée."""
        raise TODO


class TestM21QuickBall:
    pytestmark = pytest.mark.skip(reason="Jalon 6 — Quick Ball (checklist manuelle)")

    def test_floating_bubble_capture_and_habit_checkin(self):
        """Bulle flottante : capture rapide et check-in d'habitude (sans dictée)."""
        raise TODO


class TestM01GeofenceReminders:
    pytestmark = pytest.mark.skip(reason="Jalon 6 — Rappels géolocalisés")

    def test_location_reminder_on_arrival_or_departure(self):
        """Rappel déclenché à l'arrivée/au départ d'un rayon autour d'un lieu."""
        raise TODO


class TestM22FocusEnforcement:
    pytestmark = pytest.mark.skip(reason="Jalon 6 — Strict mode & Flip Start (checklist manuelle)")

    def test_strict_mode_aborts_on_app_switch(self):
        """Strict mode : quitter l'app annule la session et perd les données."""
        raise TODO

    def test_strict_mode_allowlist_exempts_apps(self):
        """Les apps de l'allowlist (ex. Spotify) ne cassent pas la session."""
        raise TODO

    def test_flip_start_runs_only_facedown(self):
        """Flip Start : le timer ne tourne que téléphone face contre table."""
        raise TODO
