"""Jalon 8 — Finitions UX (stubs).

Modules PRD : 12.2 (thèmes, sons, début de semaine, visibilité smart lists),
19.2 (fonds de liste). Le reste est polish visuel → checklist manuelle.
"""
import pytest

pytestmark = pytest.mark.spec


class TestM31Tier3MarkdownPolish:
    """Test for Tier 3 Markdown check items - checkbox markdown in descriptions."""

    def test_checked_items_sort_to_bottom(self, api, inbox):
        """Cocher un check item le place en bas de la liste (tri backend : is_done, sort_order)."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}).json()
        task_id = task["id"]

        # Créer 3 CheckItems (Tier 2) manuellement
        a = api.post("/api/check-items/", {"task": task_id, "title": "A", "sort_order": 1}).json()
        b = api.post("/api/check-items/", {"task": task_id, "title": "B", "sort_order": 2}).json()
        c = api.post("/api/check-items/", {"task": task_id, "title": "C", "sort_order": 3}).json()

        # Cocher le premier item
        api.patch(f"/api/check-items/{a['id']}/", {"is_done": True})

        # Récupérer la tâche — l'item coché doit être en dernier
        items = api.get(f"/api/tasks/{task_id}/").json()["check_items"]
        assert len(items) == 3
        assert items[-1]["id"] == a["id"]   # A coché → trié en bas
        assert items[0]["id"] == b["id"]    # B et C toujours en tête
        assert items[1]["id"] == c["id"]
