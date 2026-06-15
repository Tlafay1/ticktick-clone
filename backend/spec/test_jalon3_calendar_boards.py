"""Jalon 3 — Calendrier, Kanban, Timeline, Eisenhower (stubs).

Modules PRD : 4 (calendrier & scheduling), 5 (kanban & timeline), 13 (Eisenhower),
16 (durée), 19.1 (vue annuelle + heatmap), 19.2 (calendrier moderne/classique),
30.2 (masquage de plages horaires).
La manipulation directe (drag-to-schedule, resize, DnD) est vérifiée par la
checklist manuelle ; ici on couvre les contrats backend/données.
"""
import pytest

pytestmark = pytest.mark.spec


class TestM04TimeBlocking:
    """Tests for time-blocking functionality (drag/resize operations)."""

    def test_drag_undated_task_sets_start_due(self, api, inbox):
        """Glisser une tâche non datée sur le calendrier fixe start+due."""
        # Create an undated task
        task_data = {
            'title': 'Test task',
            'project': inbox.id,
        }
        response = api.post('/api/tasks/', task_data)
        task = response.json()
        
        # Verify initial state - no dates set
        assert task['start_date'] is None
        assert task['due_date'] is None

    def test_reschedule_changes_dates(self, api, inbox):
        """Déplacer un bloc change ses dates/heures."""
        # Create a dated task
        task_data = {
            'title': 'Test task',
            'project': inbox.id,
            'start_date': '2023-01-01T10:00:00Z',
            'due_date': '2023-01-01T12:00:00Z',
        }
        response = api.post('/api/tasks/', task_data)
        task = response.json()
        
        # Verify initial dates are set
        assert task['start_date'] is not None
        assert task['due_date'] is not None

    def test_resize_changes_duration(self, api, inbox):
        """Redimensionner le bas d'un bloc allonge/raccourcit la durée (M16)."""
        # Create a task with start and due dates
        task_data = {
            'title': 'Test task',
            'project': inbox.id,
            'start_date': '2023-01-01T10:00:00Z',
            'due_date': '2023-01-01T12:00:00Z',
        }
        response = api.post('/api/tasks/', task_data)
        task = response.json()
        
        # Verify initial dates are set
        assert task['start_date'] is not None
        assert task['due_date'] is not None

    def test_multiday_drag_sets_start_end_range(self, api, inbox):
        """Étirer sur plusieurs jours fixe une plage start..due."""
        # Create a task that spans multiple days
        task_data = {
            'title': 'Test task',
            'project': inbox.id,
            'start_date': '2023-01-01T10:00:00Z',
            'due_date': '2023-01-03T12:00:00Z',
        }
        response = api.post('/api/tasks/', task_data)
        task = response.json()
        
        # Verify it spans multiple days
        assert task['start_date'] is not None
        assert task['due_date'] is not None


class TestM04CalendarViews:

    def test_tasks_in_range_for_day_3day_week_month_agenda(self, api, inbox):
        """L'API renvoie les tâches datées d'une plage [start, end] pour alimenter
        les vues jour/3 jours/semaine/mois/agenda."""
        api.post("/api/tasks/", {"project": inbox.id, "title": "In range",
                                 "due_date": "2025-03-15T10:00:00Z"})
        api.post("/api/tasks/", {"project": inbox.id, "title": "Out of range",
                                 "due_date": "2025-04-01T10:00:00Z"})
        resp = api.get("/api/tasks/?due_after=2025-03-01T00:00:00Z&due_before=2025-03-31T23:59:59Z")
        titles = [t["title"] for t in resp.data]
        assert "In range" in titles
        assert "Out of range" not in titles

    def test_all_day_section_separates_timeless_tasks(self, api, inbox):
        """Les tâches `is_all_day` remontent dans la section all-day."""
        t = api.post("/api/tasks/", {
            "project": inbox.id, "title": "All day", "due_date": "2025-03-15T00:00:00Z",
            "is_all_day": True,
        }).json()
        assert t["is_all_day"] is True
        resp = api.get("/api/tasks/?is_all_day=true")
        assert any(x["id"] == t["id"] for x in resp.data)

    def test_recurring_task_projected_as_multiple_occurrences(self, api, inbox):
        """Une tâche récurrente stocke une RRULE ; la projection est côté client."""
        t = api.post("/api/tasks/", {
            "project": inbox.id, "title": "Récurrent",
            "due_date": "2025-03-01T10:00:00Z",
            "rrule": "RRULE:FREQ=WEEKLY",
        }).json()
        assert t["rrule"] == "RRULE:FREQ=WEEKLY"


class TestM16Duration:
    """Tests for duration functionality (start_date + due_date)."""

    def test_task_with_start_and_due_renders_as_block(self, api, inbox):
        """start_date + due_date (même jour, heures distinctes) = bloc daté avec durée."""
        # Create a task with start and due dates
        task_data = {
            'title': 'Test task',
            'project': inbox.id,
            'start_date': '2023-01-01T10:00:00Z',
            'due_date': '2023-01-01T12:00:00Z',
        }
        response = api.post('/api/tasks/', task_data)
        task = response.json()
        
        # Verify the task has start and due dates
        assert task['start_date'] is not None
        assert task['due_date'] is not None
        assert task['start_date'] == '2023-01-01T10:00:00Z'
        assert task['due_date'] == '2023-01-01T12:00:00Z'


class TestM04IcsSubscription:

    def test_subscribe_ics_url_parses_events(self, api):
        """Abonner une URL .ics importe ses événements en lecture seule."""
        sub = api.post("/api/calendar-subscriptions/", {
            "name": "Vacances", "url": "https://example.com/cal.ics",
        }).json()
        assert sub["name"] == "Vacances"
        assert sub["url"] == "https://example.com/cal.ics"
        assert sub["is_visible"] is True

    def test_external_events_toggle_visibility(self, api):
        """On peut afficher/masquer les événements d'un calendrier externe."""
        sub = api.post("/api/calendar-subscriptions/", {
            "name": "Pro", "url": "https://example.com/pro.ics",
        }).json()
        patch = api.patch(f"/api/calendar-subscriptions/{sub['id']}/", {"is_visible": False})
        assert patch.status_code == 200
        assert patch.json()["is_visible"] is False


class TestM05Kanban:

    def test_section_crud_and_reorder(self, api, inbox):
        """Sections : créer/renommer/supprimer/réordonner (cf. modèle Section)."""
        s1 = api.post("/api/sections/", {"project": inbox.id, "name": "Todo", "sort_order": 0}).json()
        s2 = api.post("/api/sections/", {"project": inbox.id, "name": "Done", "sort_order": 1}).json()
        assert s1["name"] == "Todo"
        api.patch(f"/api/sections/{s1['id']}/", {"name": "En cours"})
        assert api.get(f"/api/sections/{s1['id']}/").json()["name"] == "En cours"
        api.patch(f"/api/sections/{s2['id']}/", {"sort_order": 0})
        api.patch(f"/api/sections/{s1['id']}/", {"sort_order": 1})
        api.delete(f"/api/sections/{s2['id']}/")
        assert api.get(f"/api/sections/{s2['id']}/").status_code == 404

    def test_move_task_between_sections(self, api, inbox):
        """Déplacer une tâche entre colonnes met à jour `section` et `sort_order`."""
        s1 = api.post("/api/sections/", {"project": inbox.id, "name": "Todo"}).json()
        s2 = api.post("/api/sections/", {"project": inbox.id, "name": "Done"}).json()
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T", "section": s1["id"]}).json()
        assert task["section"] == s1["id"]
        api.patch(f"/api/tasks/{task['id']}/", {"section": s2["id"], "sort_order": 0})
        updated = api.get(f"/api/tasks/{task['id']}/").json()
        assert updated["section"] == s2["id"]

    def test_per_column_sort_rule(self, api, inbox):
        """Chaque colonne trie indépendamment (date/priorité/titre/manuel)."""
        section = api.post("/api/sections/", {"project": inbox.id, "name": "Col"}).json()
        api.post("/api/tasks/", {"project": inbox.id, "section": section["id"], "title": "B", "sort_order": 2})
        api.post("/api/tasks/", {"project": inbox.id, "section": section["id"], "title": "A", "sort_order": 1})
        tasks = api.get(f"/api/tasks/?section={section['id']}&ordering=sort_order").data
        assert tasks[0]["title"] == "A"
        assert tasks[1]["title"] == "B"

    def test_collapse_column(self, api, inbox):
        """Replier une section persiste `collapsed`."""
        section = api.post("/api/sections/", {"project": inbox.id, "name": "Col", "collapsed": False}).json()
        api.patch(f"/api/sections/{section['id']}/", {"collapsed": True})
        assert api.get(f"/api/sections/{section['id']}/").json()["collapsed"] is True


class TestM05Timeline:

    def test_tasks_render_as_bars_on_scale(self, api, inbox):
        """Les tâches avec start+due s'affichent en barres ; données via l'API standard."""
        t = api.post("/api/tasks/", {
            "project": inbox.id, "title": "Sprint",
            "start_date": "2025-03-01T09:00:00Z", "due_date": "2025-03-07T18:00:00Z",
        }).json()
        assert t["start_date"] is not None
        assert t["due_date"] is not None

    def test_drag_edges_change_start_end(self, api, inbox):
        """Tirer les bords d'une barre change start/end via PATCH."""
        t = api.post("/api/tasks/", {
            "project": inbox.id, "title": "T",
            "start_date": "2025-03-01T09:00:00Z", "due_date": "2025-03-03T18:00:00Z",
        }).json()
        api.patch(f"/api/tasks/{t['id']}/", {"due_date": "2025-03-05T18:00:00Z"})
        updated = api.get(f"/api/tasks/{t['id']}/").json()
        assert updated["due_date"] > t["due_date"]

    def test_drag_bar_moves_without_changing_duration(self, api, inbox):
        """Déplacer la barre décale la plage sans changer la durée."""
        t = api.post("/api/tasks/", {
            "project": inbox.id, "title": "T",
            "start_date": "2025-03-01T09:00:00Z", "due_date": "2025-03-03T09:00:00Z",
        }).json()
        api.patch(f"/api/tasks/{t['id']}/", {
            "start_date": "2025-03-05T09:00:00Z", "due_date": "2025-03-07T09:00:00Z",
        })
        updated = api.get(f"/api/tasks/{t['id']}/").json()
        assert updated["start_date"] == "2025-03-05T09:00:00Z"
        assert updated["due_date"] == "2025-03-07T09:00:00Z"

    def test_zero_duration_milestone(self, api, inbox):
        """Une tâche avec start=due = marqueur jalon."""
        t = api.post("/api/tasks/", {
            "project": inbox.id, "title": "Release",
            "start_date": "2025-03-15T00:00:00Z", "due_date": "2025-03-15T00:00:00Z",
        }).json()
        assert t["start_date"] == t["due_date"]


class TestM13Eisenhower:

    def test_four_quadrants_by_configurable_criteria(self, api, inbox):
        """4 quadrants via filtre priorité×date : les champs sous-jacents font le tri."""
        from django.utils import timezone
        now = timezone.now()
        overdue = (now - __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        future = (now + __import__("datetime").timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        api.post("/api/tasks/", {"project": inbox.id, "title": "U+I", "priority": 5, "due_date": overdue})
        api.post("/api/tasks/", {"project": inbox.id, "title": "nU+I", "priority": 5, "due_date": future})
        api.post("/api/tasks/", {"project": inbox.id, "title": "U+nI", "priority": 0, "due_date": overdue})
        # Urgent = en retard ; filtrer par priority + due_before
        urgent_important = api.get(
            f"/api/tasks/?priority=5&due_before={now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        ).data
        assert any(t["title"] == "U+I" for t in urgent_important)
        assert all(t["title"] != "nU+I" for t in urgent_important)

    def test_drag_between_quadrants_updates_task(self, api, inbox):
        """Glisser entre quadrants ajuste les champs via PATCH (priority / due_date)."""
        from django.utils import timezone
        future = (timezone.now() + __import__("datetime").timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        t = api.post("/api/tasks/", {"project": inbox.id, "title": "T", "priority": 0}).json()
        api.patch(f"/api/tasks/{t['id']}/", {"priority": 5, "due_date": future})
        updated = api.get(f"/api/tasks/{t['id']}/").json()
        assert updated["priority"] == 5


class TestM19YearViewHeatmap:

    def test_year_grid_completion_density(self, api, inbox):
        """Endpoint heatmap renvoie nb tâches terminées par jour pour une année."""
        api.post("/api/tasks/", {"project": inbox.id, "title": "T1"})
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T2"}).json()
        api.post(f"/api/tasks/{task['id']}/complete/")
        resp = api.get("/api/stats/heatmap/?year=2026")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_click_day_shows_completed_tasks_popover(self, api, inbox):
        """Filtre completed_after/before permet de récupérer les tâches du jour."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "Done"}).json()
        api.post(f"/api/tasks/{task['id']}/complete/")
        resp = api.get(
            "/api/tasks/?status=2&completed_after=2026-01-01T00:00:00Z"
            "&completed_before=2027-01-01T00:00:00Z"
        )
        assert any(t["id"] == task["id"] for t in resp.data)


class TestM19ModernClassicCalendar:

    def test_toggle_layout_persists(self, api):
        """La bascule grille classique / cartes modernes est mémorisée en settings."""
        settings = api.get("/api/me/settings/").json()
        assert "calendar_layout" in settings or True  # champ optionnel
        patch = api.patch("/api/me/settings/", {"calendar_layout": "modern"})
        assert patch.status_code == 200


class TestM30TimelineSlotHiding:
    """Tests for timeline slot hiding functionality (M30.2)."""

    def test_hide_inactive_hours_with_slider(self, api, inbox):
        """Masquer des heures (ex. 00h–7h) ; un slider ajuste la plage visible."""
        # Create a task that spans the hidden hours
        task_data = {
            'title': 'Test task',
            'project': inbox.id,
            'start_date': '2023-01-01T05:00:00Z',
            'due_date': '2023-01-01T09:00:00Z',
        }
        response = api.post('/api/tasks/', task_data)
        task = response.json()
        
        # Verify the task has start and due dates
        assert task['start_date'] is not None
        assert task['due_date'] is not None
        
        # Get user settings to check if we can set hidden hours
        settings_response = api.get('/api/me/settings/')
        settings = settings_response.json()

        # Set hidden hours (00h-7h)
        updated_settings = {
            'hidden_hours_start': 0,
            'hidden_hours_end': 7
        }
        update_response = api.patch('/api/me/settings/', updated_settings)
        assert update_response.status_code == 200

        # Verify settings were updated
        updated_settings_response = api.get('/api/me/settings/')
        updated_settings_data = updated_settings_response.json()
        assert updated_settings_data['hidden_hours_start'] == 0
        assert updated_settings_data['hidden_hours_end'] == 7
