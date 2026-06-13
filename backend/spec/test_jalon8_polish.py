"""Jalon 8 — Finitions UX (stubs).

Modules PRD : 12.2 (thèmes, sons, début de semaine, visibilité smart lists),
19.2 (fonds de liste). Le reste est polish visuel → checklist manuelle.
"""
import pytest

pytestmark = pytest.mark.spec
TODO = NotImplementedError


class TestM12ThemesAndPrefs:
    pytestmark = pytest.mark.skip(reason="Jalon 8 — Thèmes & préférences")

    def test_theme_light_dark_auto_and_presets(self):
        """Thèmes clair/sombre/auto + presets de couleurs (Lavender, Forest…)."""
        raise TODO

    def test_custom_reminder_sounds(self):
        """Choix d'un son de rappel parmi une collection."""
        raise TODO

    def test_week_start_day_sun_mon_sat(self):
        """Début de semaine configurable (dim/lun/sam) respecté par les vues."""
        raise TODO

    def test_smart_list_visibility_toggle(self):
        """Afficher/masquer les smart lists par défaut (Demain, 7 jours, Terminées)."""
        raise TODO


class TestM19ListBackgrounds:
    pytestmark = pytest.mark.skip(reason="Jalon 8 — Fonds de liste")

    def test_custom_background_per_list(self):
        """Fond (wallpaper/motif/couleur) défini par liste."""
        raise TODO


class TestM31Tier3MarkdownPolish:
    pytestmark = pytest.mark.skip(reason="Jalon 8 — Polish (auto-sort, animations)")

    def test_checked_items_animate_to_bottom(self):
        """Cocher un check item l'anime vers le bas de la checklist (déjà trié backend)."""
        raise TODO
