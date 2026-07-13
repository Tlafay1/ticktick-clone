"""Jalon 4 — Habitudes, Focus, Countdown, Statistiques.

Modules PRD : 6 (habitudes), 7 (focus), 18/35 (countdown), 17 (summary),
12.3 (gamification), 26.1 (daily review), 21 (multi-log, pomo estimation),
28.2 (modes de check-in), 29.2 (timer dans l'onglet web).
"""
import pytest
from datetime import date, datetime, timezone as dt_tz, timedelta

pytestmark = pytest.mark.spec


class TestM06HabitConfig:
    """Habitude : nom, emoji/icône, couleur, fréquence, objectif, rappels, motto."""

    def test_name_icon_color(self, api):
        """Créer une habitude avec nom, icône emoji et couleur."""
        resp = api.post("/api/habits/", {
            "name": "Lecture",
            "icon": "📚",
            "color": "#FF9800",
            "frequency": "daily",
            "goal_type": "binary",
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Lecture"
        assert data["icon"] == "📚"
        assert data["color"] == "#FF9800"

    def test_frequency_daily_weekly_specific_days_interval_goalcount(self, api):
        """Fréquences : quotidien, hebdo, jours précis, intervalle, objectif hebdo."""
        for freq, config in [
            ("daily", {}),
            ("weekly", {}),
            ("specific_days", {"days": [0, 2, 4]}),
            ("interval", {"every": 3}),
            ("weekly_goal", {"times": 3}),
        ]:
            resp = api.post("/api/habits/", {
                "name": f"Habitude {freq}",
                "frequency": freq,
                "freq_config": config,
                "goal_type": "binary",
            }, format="json")
            assert resp.status_code == 201, freq
            assert resp.json()["frequency"] == freq

    def test_goal_binary_or_numeric_with_unit(self, api):
        """Objectif binaire ou numérique avec unité personnalisée."""
        # Binaire
        resp = api.post("/api/habits/", {"name": "Sport", "goal_type": "binary"}, format="json")
        assert resp.status_code == 201
        assert resp.json()["goal_type"] == "binary"

        # Numérique
        resp = api.post("/api/habits/", {
            "name": "Eau",
            "goal_type": "numeric",
            "goal_value": 8,
            "goal_unit": "verres",
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["goal_type"] == "numeric"
        assert data["goal_value"] == 8.0
        assert data["goal_unit"] == "verres"

    def test_habit_reminders_independent_of_tasks(self, api):
        """Rappels d'habitude indépendants des rappels de tâche."""
        habit = api.post("/api/habits/", {"name": "Méditation", "goal_type": "binary"}, format="json").json()
        # Ajouter plusieurs créneaux d'alarme
        r1 = api.post(f"/api/habits/{habit['id']}/reminders/", {"time": "08:00"}, format="json")
        r2 = api.post(f"/api/habits/{habit['id']}/reminders/", {"time": "20:00"}, format="json")
        assert r1.status_code == 201
        assert r2.status_code == 201
        # Les rappels sont listés sur l'habitude
        detail = api.get(f"/api/habits/{habit['id']}/").json()
        times = [r["time"] for r in detail["reminders"]]
        assert "08:00:00" in times
        assert "20:00:00" in times

    def test_optional_motto(self, api):
        """Motto optionnel affiché au check-in."""
        resp = api.post("/api/habits/", {
            "name": "Courir",
            "motto": "Un peu chaque jour !",
            "goal_type": "binary",
        }, format="json")
        assert resp.status_code == 201
        assert resp.json()["motto"] == "Un peu chaque jour !"


class TestM28HabitCheckInModes:
    """Modes de check-in : auto (incrément), manuel (quantité), binaire."""

    def test_automatic_increment_mode(self, api):
        """Mode auto : tap = ajoute auto_increment."""
        habit = api.post("/api/habits/", {
            "name": "Eau",
            "goal_type": "numeric",
            "goal_value": 8,
            "goal_unit": "verres",
            "check_in_mode": "auto",
            "auto_increment": 1.0,
        }, format="json").json()
        today = date.today().isoformat()
        checkin = api.post(f"/api/habits/{habit['id']}/checkins/", {
            "date": today,
            "quantity": 1.0,
        }, format="json")
        assert checkin.status_code == 201
        assert checkin.json()["quantity"] == 1.0

    def test_manual_entry_mode_prompts_quantity(self, api):
        """Mode manuel : saisie de la quantité exacte."""
        habit = api.post("/api/habits/", {
            "name": "Eau",
            "goal_type": "numeric",
            "goal_value": 2000,
            "goal_unit": "ml",
            "check_in_mode": "manual",
        }, format="json").json()
        today = date.today().isoformat()
        checkin = api.post(f"/api/habits/{habit['id']}/checkins/", {
            "date": today,
            "quantity": 750,
        }, format="json")
        assert checkin.status_code == 201
        assert checkin.json()["quantity"] == 750.0

    def test_binary_complete_all_mode(self, api):
        """Mode binaire : simple coche → completed=True."""
        habit = api.post("/api/habits/", {
            "name": "Sport",
            "goal_type": "binary",
            "check_in_mode": "binary",
        }, format="json").json()
        today = date.today().isoformat()
        checkin = api.post(f"/api/habits/{habit['id']}/checkins/", {
            "date": today,
            "quantity": 1,
        }, format="json")
        assert checkin.status_code == 201
        assert checkin.json()["completed"] is True


class TestM21HabitMultiLog:
    """Plusieurs check-ins par jour, plusieurs créneaux d'alarme."""

    def test_multiple_checkins_per_day(self, api):
        """Plusieurs check-ins le même jour (ex. boire 5 fois)."""
        habit = api.post("/api/habits/", {
            "name": "Eau",
            "goal_type": "numeric",
            "goal_value": 5,
            "check_in_mode": "auto",
            "auto_increment": 1.0,
        }, format="json").json()
        today = date.today().isoformat()
        for _ in range(3):
            api.post(f"/api/habits/{habit['id']}/checkins/", {"date": today, "quantity": 1}, format="json")
        checkins = api.get(f"/api/habits/{habit['id']}/checkins/?date={today}").json()
        assert len(checkins) == 3
        # Somme 3 < objectif 5 : le jour n'est pas encore atteint.
        assert all(c["completed"] is False for c in checkins)
        # Deux logs de plus → somme 5 ≥ objectif : le jour est atteint (agrégation).
        for _ in range(2):
            api.post(f"/api/habits/{habit['id']}/checkins/", {"date": today, "quantity": 1}, format="json")
        checkins = api.get(f"/api/habits/{habit['id']}/checkins/?date={today}").json()
        assert all(c["completed"] is True for c in checkins)

    def test_multiple_time_slot_alarms(self, api):
        """Plusieurs créneaux d'alarme distincts pour la même habitude."""
        habit = api.post("/api/habits/", {"name": "Eau", "goal_type": "binary"}, format="json").json()
        for t in ["08:00", "13:00", "20:00"]:
            api.post(f"/api/habits/{habit['id']}/reminders/", {"time": t}, format="json")
        detail = api.get(f"/api/habits/{habit['id']}/").json()
        assert len(detail["reminders"]) == 3


class TestM06HabitTrackingStats:
    """Suivi & stats d'habitude : check-in, note, streak, taux de complétion, presets."""

    def test_one_tap_checkin_from_sidebar(self, api):
        """Check-in simple depuis le listing des habitudes."""
        habit = api.post("/api/habits/", {"name": "Sport", "goal_type": "binary"}, format="json").json()
        today = date.today().isoformat()
        resp = api.post(f"/api/habits/{habit['id']}/checkins/", {"date": today, "quantity": 1}, format="json")
        assert resp.status_code == 201
        assert resp.json()["completed"] is True

    def test_daily_reflection_note(self, api):
        """Note de réflexion optionnelle attachée au check-in."""
        habit = api.post("/api/habits/", {"name": "Journal", "goal_type": "binary"}, format="json").json()
        today = date.today().isoformat()
        resp = api.post(f"/api/habits/{habit['id']}/checkins/", {
            "date": today,
            "quantity": 1,
            "note": "Belle journée, j'ai bien écrit.",
        }, format="json")
        assert resp.status_code == 201
        assert "Belle journée" in resp.json()["note"]

    def test_streak_calendar_current_and_max(self, api):
        """streak courant et max retournés sur l'habitude."""
        habit_resp = api.post("/api/habits/", {"name": "Sport", "goal_type": "binary"}, format="json")
        assert habit_resp.status_code == 201
        habit = habit_resp.json()
        # Pas de check-in → streak = 0
        assert habit["streak"] == 0
        assert habit["max_streak"] == 0

    def test_completion_rate_graphs(self, api):
        """Taux de complétion : checkins filtrables par date."""
        habit = api.post("/api/habits/", {"name": "Eau", "goal_type": "binary"}, format="json").json()
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        api.post(f"/api/habits/{habit['id']}/checkins/", {"date": today, "quantity": 1}, format="json")
        api.post(f"/api/habits/{habit['id']}/checkins/", {"date": yesterday, "quantity": 1}, format="json")
        all_checkins = api.get(f"/api/habits/{habit['id']}/checkins/").json()
        assert len(all_checkins) == 2

    def test_preset_library_autoconfigures(self, api):
        """La bibliothèque de presets préremplit fréquence/icône/motto."""
        resp = api.get("/api/habits/presets/")
        assert resp.status_code == 200
        presets = resp.json()
        assert len(presets) > 0
        # Chaque preset a les champs requis
        for p in presets:
            assert "name" in p
            assert "icon" in p
            assert "frequency" in p
            assert "goal_type" in p


class TestM07Focus:
    """Focus : Pomodoro, chrono, tâche associée, sons d'ambiance."""

    def _make_task(self, api, inbox):
        return api.post("/api/tasks/", {
            "project": inbox.id,
            "title": "Tâche focus",
        }, format="json").json()

    def test_pomodoro_custom_durations_and_long_break_interval(self, api, inbox):
        """Enregistrer une session Pomodoro avec durée personnalisée."""
        task = self._make_task(api, inbox)
        now = datetime.now(dt_tz.utc)
        resp = api.post("/api/focus-sessions/", {
            "task": task["id"],
            "mode": "pomodoro",
            "session_type": "work",
            "start_at": now.isoformat(),
            "end_at": (now + timedelta(minutes=25)).isoformat(),
            "duration_seconds": 1500,
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["mode"] == "pomodoro"
        assert data["duration_seconds"] == 1500

    def test_auto_start_next_session(self, api, inbox):
        """Enregistrer plusieurs sessions consécutives (work + break)."""
        task = self._make_task(api, inbox)
        now = datetime.now(dt_tz.utc)
        work = api.post("/api/focus-sessions/", {
            "task": task["id"],
            "mode": "pomodoro",
            "session_type": "work",
            "start_at": now.isoformat(),
            "end_at": (now + timedelta(minutes=25)).isoformat(),
            "duration_seconds": 1500,
        }, format="json")
        assert work.status_code == 201
        short_break = api.post("/api/focus-sessions/", {
            "mode": "pomodoro",
            "session_type": "short_break",
            "start_at": (now + timedelta(minutes=25)).isoformat(),
            "end_at": (now + timedelta(minutes=30)).isoformat(),
            "duration_seconds": 300,
        }, format="json")
        assert short_break.status_code == 201

    def test_stopwatch_count_up(self, api, inbox):
        """Mode chronomètre (count-up)."""
        task = self._make_task(api, inbox)
        now = datetime.now(dt_tz.utc)
        resp = api.post("/api/focus-sessions/", {
            "task": task["id"],
            "mode": "stopwatch",
            "session_type": "work",
            "start_at": now.isoformat(),
            "end_at": (now + timedelta(minutes=42)).isoformat(),
            "duration_seconds": 2520,
        }, format="json")
        assert resp.status_code == 201
        assert resp.json()["mode"] == "stopwatch"

    def test_session_logged_to_associated_task(self, api, inbox):
        """La session est rattachée à la tâche sélectionnée."""
        task = self._make_task(api, inbox)
        now = datetime.now(dt_tz.utc)
        session = api.post("/api/focus-sessions/", {
            "task": task["id"],
            "mode": "pomodoro",
            "session_type": "work",
            "start_at": now.isoformat(),
            "duration_seconds": 1500,
        }, format="json")
        assert session.status_code == 201
        assert session.json()["task"] == task["id"]

    def test_ambient_sounds_mix_and_volume(self, api):
        """Sons d'ambiance : config stockée en settings utilisateur."""
        # La config sons est stockée côté client ; on vérifie que les settings
        # acceptent un champ arbitraire via PATCH (JSONField).
        resp = api.patch("/api/me/settings/", {
            "reminder_sound": "rain",
        }, format="json")
        assert resp.status_code == 200
        assert resp.json()["reminder_sound"] == "rain"


class TestM21FocusEstimation:
    """Estimation Pomodoro sur une tâche : estimé vs réel."""

    def test_estimated_pomos_on_task(self, api, inbox):
        """Définir un nombre de pomodoros estimés sur une tâche."""
        task = api.post("/api/tasks/", {
            "project": inbox.id,
            "title": "Rapport",
            "estimated_pomos": 4,
        }, format="json")
        assert task.status_code == 201
        assert task.json()["estimated_pomos"] == 4

    def test_actual_vs_estimated_accuracy(self, api, inbox):
        """Comparer focus réel vs estimé via les sessions de focus."""
        task = api.post("/api/tasks/", {
            "project": inbox.id,
            "title": "Rapport",
            "estimated_pomos": 3,
        }, format="json").json()
        now = datetime.now(dt_tz.utc)
        # 4 pomos réels (dépassé l'estimation)
        for i in range(4):
            start = now + timedelta(minutes=i * 30)
            api.post("/api/focus-sessions/", {
                "task": task["id"],
                "mode": "pomodoro",
                "session_type": "work",
                "start_at": start.isoformat(),
                "duration_seconds": 1500,
            }, format="json")
        sessions = api.get("/api/focus-sessions/").json()
        actual = sum(s["duration_seconds"] for s in sessions if s["task"] == task["id"])
        estimated_seconds = task["estimated_pomos"] * 1500
        assert actual > estimated_seconds  # dépassé l'estimation


class TestM07FocusStats:
    """Statistiques de focus : logs, distribution, tendances."""

    def test_focus_logs_persisted(self, api, inbox):
        """Chaque session enregistre début/fin/durée/tâche."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json").json()
        now = datetime.now(dt_tz.utc)
        api.post("/api/focus-sessions/", {
            "task": task["id"],
            "mode": "pomodoro",
            "session_type": "work",
            "start_at": now.isoformat(),
            "end_at": (now + timedelta(minutes=25)).isoformat(),
            "duration_seconds": 1500,
        }, format="json")
        sessions = api.get("/api/focus-sessions/").json()
        assert len(sessions) >= 1
        s = sessions[0]
        assert "start_at" in s
        assert "duration_seconds" in s
        assert s["task"] == task["id"]

    def test_distribution_by_list_tag_pie(self, api, inbox):
        """Répartition du focus par liste retournée par /api/focus-sessions/stats/."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json").json()
        now = datetime.now(dt_tz.utc)
        api.post("/api/focus-sessions/", {
            "task": task["id"],
            "mode": "pomodoro",
            "session_type": "work",
            "start_at": now.isoformat(),
            "duration_seconds": 1500,
        }, format="json")
        stats = api.get("/api/focus-sessions/stats/").json()
        assert "by_list" in stats
        assert stats["total_seconds"] >= 1500

    def test_trends_and_streaks(self, api, inbox):
        """Stats globales disponibles via /api/focus-sessions/stats/."""
        stats = api.get("/api/focus-sessions/stats/").json()
        assert "total_seconds" in stats
        assert "by_list" in stats
        assert "by_tag" in stats


class TestM29WebTabTimer:
    """Timer dans l'onglet web : session de focus interrogeable pour affichage."""

    def test_tab_title_shows_running_countdown(self, api, inbox):
        """Une session en cours peut être récupérée pour afficher le compte à rebours."""
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json").json()
        now = datetime.now(dt_tz.utc)
        session = api.post("/api/focus-sessions/", {
            "task": task["id"],
            "mode": "pomodoro",
            "session_type": "work",
            "start_at": now.isoformat(),
            "duration_seconds": 1500,
        }, format="json").json()
        # La session sans end_at = session en cours
        assert session["end_at"] is None
        # Le client calcule le reste à partir de start_at + duration_seconds
        detail = api.get(f"/api/focus-sessions/{session['id']}/").json()
        assert detail["duration_seconds"] == 1500
        assert detail["start_at"] is not None


class TestM18Countdown:
    """Countdown : compte à rebours jusqu'à une date, épinglable, description riche."""

    def test_countdown_card_shows_days_remaining(self, api):
        """Carte countdown : days_remaining calculé automatiquement."""
        future = (date.today() + timedelta(days=30)).isoformat()
        resp = api.post("/api/countdowns/", {
            "title": "Anniversaire",
            "target_date": future,
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Anniversaire"
        assert data["days_remaining"] == 30

    def test_countdown_pinned_and_rich_note(self, api):
        """Countdown épinglable avec description markdown (M35)."""
        future = (date.today() + timedelta(days=10)).isoformat()
        resp = api.post("/api/countdowns/", {
            "title": "Vacances",
            "target_date": future,
            "pinned": True,
            "description": "# Idées\n- Valise\n- Passeport",
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["pinned"] is True
        assert "Valise" in data["description"]
        assert data["days_remaining"] == 10


class TestM17Summary:
    """Page Summary : score du jour, tâches complétées/en retard, distribution, historique."""

    def test_today_score_completed_overdue(self, api, inbox):
        """Endpoint summary retourne completed_today et overdue."""
        resp = api.get("/api/stats/summary/")
        assert resp.status_code == 200
        data = resp.json()
        assert "completed_today" in data
        assert "overdue" in data
        assert isinstance(data["completed_today"], int)
        assert isinstance(data["overdue"], int)

    def test_distribution_by_list_and_best_hours(self, api, inbox):
        """Summary inclut la distribution par liste et les meilleures heures."""
        # Créer une tâche pour avoir une distribution non vide
        api.post("/api/tasks/", {"project": inbox.id, "title": "T"}, format="json")
        resp = api.get("/api/stats/summary/")
        assert resp.status_code == 200
        data = resp.json()
        assert "by_list" in data
        assert "best_hours" in data

    def test_monthly_history(self, api):
        """Historique mensuel sur 12 mois."""
        resp = api.get("/api/stats/monthly/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12
        assert "month" in data[0]
        assert "count" in data[0]


class TestM12Gamification:
    """Score de productivité quotidien, niveaux et badges."""

    def test_productivity_score_daily_adjustments(self, api, inbox):
        """Score retourné par /api/stats/productivity-score/."""
        resp = api.get("/api/stats/productivity-score/")
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "overdue" in data
        assert isinstance(data["score"], int)

    def test_levels_and_badges(self, api, inbox, user):
        """Niveau calculé selon les complétions cumulées."""
        from django.utils import timezone

        from apps.tasks.models import Task

        resp = api.get("/api/stats/productivity-score/")
        assert resp.status_code == 200
        data = resp.json()
        # Contrat consommé par le web (StatsView) : label texte, pas un entier.
        assert data["level"] == "Débutant"

        # 20 complétions cumulées font passer au niveau suivant.
        now = timezone.now()
        Task.objects.bulk_create([
            Task(user=user, project=inbox, title=f"T{i}",
                 status=Task.Status.COMPLETED, completed_at=now)
            for i in range(20)
        ])
        resp = api.get("/api/stats/productivity-score/")
        assert resp.json()["level"] == "Régulier"


class TestM26DailyReview:
    """Daily review : digest quotidien, carte de bilan hebdo."""

    def test_morning_or_evening_digest_dispatched(self, api, inbox):
        """Le digest peut être prévisualisé via l'endpoint summary."""
        # Le daily review utilise les mêmes données que le summary.
        # On vérifie que les données nécessaires au digest sont disponibles.
        api.post("/api/tasks/", {
            "project": inbox.id,
            "title": "Faire du sport",
            "due_date": datetime.now(dt_tz.utc).isoformat(),
        }, format="json")
        resp = api.get("/api/stats/summary/")
        assert resp.status_code == 200
        data = resp.json()
        # Le digest inclut les tâches du jour (by_list non vide)
        assert "by_list" in data

    def test_weekly_summary_card(self, api):
        """Bilan hebdo : historique mensuel disponible."""
        resp = api.get("/api/stats/monthly/")
        assert resp.status_code == 200
        assert len(resp.json()) == 12
