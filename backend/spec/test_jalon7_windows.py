"""Jalon 7 — Client Windows / Electron (stubs).

Modules PRD : 11.2 (hotkey global, tray, startup, notifs natives), 27.2 (impression
& export PDF). Comportements natifs → checklist manuelle ; les stubs tracent les
contrats de données (ex. payload d'impression). Sticky notes desktop : COUPÉES.
"""
import pytest

pytestmark = pytest.mark.spec
TODO = NotImplementedError


class TestM11Desktop:
    pytestmark = pytest.mark.skip(reason="Jalon 7 — Electron natif (checklist manuelle)")

    def test_global_hotkey_quick_add_window(self):
        """Un hotkey global ouvre une mini-fenêtre de capture, app au premier plan ou non."""
        raise TODO

    def test_tray_mini_list_and_timer_progress(self):
        """Le tray montre une mini-liste et la progression du timer de focus."""
        raise TODO

    def test_launch_minimized_on_startup(self):
        """Option de lancement minimisé dans le tray au démarrage de Windows."""
        raise TODO

    def test_native_toast_with_complete_and_snooze_actions(self):
        """Toasts natifs avec boutons « Terminer » / « Snooze »."""
        raise TODO


class TestM27Print:
    pytestmark = pytest.mark.skip(reason="Jalon 7 — Impression & export PDF")

    def test_print_lists_tasks_eisenhower(self):
        """Imprimer/PDF : listes, tâches, ou la matrice d'Eisenhower."""
        raise TODO

    def test_layout_options_subtasks_comments_compact(self):
        """Options de mise en page : inclure sous-tâches/commentaires, compact/étendu."""
        raise TODO
