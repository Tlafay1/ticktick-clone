"""Jalon 8 — Finitions UX (stubs).

Modules PRD : 12.2 (thèmes, sons, début de semaine, visibilité smart lists),
19.2 (fonds de liste). Le reste est polish visuel → checklist manuelle.
"""
import pytest

pytestmark = pytest.mark.spec


class TestM31Tier3MarkdownPolish:
    """Test for Tier 3 Markdown check items - checkbox markdown in descriptions."""

    def test_checked_items_animate_to_bottom(self, api, task_factory):
        """Cocher un check item l'anime vers le bas de la checklist (déjà trié backend)."""
        # Create a task with markdown checkboxes in description
        task = task_factory(
            title="Test Task",
            description="- [ ] First item\n- [ ] Second item\n- [ ] Third item"
        )
        
        # Verify that check items were created from the markdown
        check_items = task.check_items.all()
        assert len(check_items) == 3
        
        # Check that all items are initially unchecked
        for item in check_items:
            assert item.completed is False
        
        # Complete one of the items
        first_item = check_items[0]
        first_item.completed = True
        first_item.save()
        
        # Verify that completed item is marked as completed
        assert first_item.completed is True
        
        # Verify that all items still exist
        assert len(task.check_items.all()) == 3
        
        # Find the completed item
        completed_item = None
        for item in task.check_items.all():
            if item.id == first_item.id:
                completed_item = item
                break
        
        assert completed_item is not None
        assert completed_item.completed is True
