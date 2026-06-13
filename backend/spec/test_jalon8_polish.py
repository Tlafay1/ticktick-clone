"""Jalon 8 — Finitions UX (stubs).

Modules PRD : 12.2 (thèmes, sons, début de semaine, visibilité smart lists),
19.2 (fonds de liste). Le reste est polish visuel → checklist manuelle.
"""
import pytest

pytestmark = pytest.mark.spec


class TestM31Tier3MarkdownPolish:
    """Test for Tier 3 Markdown check items - checkbox markdown in descriptions."""

    def test_checked_items_animate_to_bottom(self, api, inbox):
        """Cocher un check item l'anime vers le bas de la checklist (déjà trié backend)."""
        # Create a task with markdown checkboxes in description
        task_data = {
            "project": inbox.id,
            "title": "Test Task",
            "description": "- [ ] First item\n- [ ] Second item\n- [ ] Third item"
        }
        response = api.post("/api/tasks/", task_data)
        assert response.status_code == 201
        task = response.json()
        
        # Verify that check items were created from the markdown
        check_items = task["check_items"]
        assert len(check_items) == 3
        
        # Check that all items are initially unchecked
        for item in check_items:
            assert item["is_done"] is False
        
        # Complete one of the items
        first_item_id = check_items[0]["id"]
        update_response = api.patch(f"/api/check-items/{first_item_id}/", {"is_done": True})
        assert update_response.status_code == 200
        
        # Verify that completed item is marked as completed
        updated_item = update_response.json()
        assert updated_item["is_done"] is True
        
        # Get the task again to verify the check items are in correct order
        get_task_response = api.get(f"/api/tasks/{task['id']}/")
        assert get_task_response.status_code == 200
        updated_task = get_task_response.json()
        
        # Verify that all items still exist
        assert len(updated_task["check_items"]) == 3
        
        # Find the completed item
        completed_item = None
        for item in updated_task["check_items"]:
            if item["id"] == first_item_id:
                completed_item = item
                break
        
        assert completed_item is not None
        assert completed_item["is_done"] is True
        
        # Verify that completed item moved to the bottom (since it's sorted by is_done, then sort_order)
        # The completed item should be at the end
        assert updated_task["check_items"][-1]["id"] == first_item_id
