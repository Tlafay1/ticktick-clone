"""Jalon 9 — Méthode d'organisation (modules 36 à 41), tests RÉELS.

Cf. docs/requirements/modules-36-41.md. Horloge figée : semaine du lundi
12 octobre 2026, utilisateur à Paris (UTC+2 à cette date). Les événements
sortants sont capturés au niveau des webhooks (contrat consommé par les agents).
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

pytestmark = pytest.mark.spec

PARIS = ZoneInfo("Europe/Paris")


def paris(day, hour, minute=0):
    """Instant à Paris, en octobre 2026."""
    return datetime(2026, 10, day, hour, minute, tzinfo=PARIS)


@pytest.fixture
def clock(monkeypatch):
    """Horloge pilotable, démarrée lundi 12 octobre 10:00 à Paris."""

    class Clock:
        now = paris(12, 10)

        def at(self, day, hour, minute=0):
            self.now = paris(day, hour, minute)

    c = Clock()
    monkeypatch.setattr("django.utils.timezone.now", lambda: c.now)
    return c


@pytest.fixture
def me(user):
    user.settings.timezone = "Europe/Paris"
    user.settings.save()
    return user


@pytest.fixture
def events(me, monkeypatch):
    """Noms (et enveloppes) des événements webhook émis pour l'utilisateur."""
    from apps.webhooks.models import Webhook

    Webhook.objects.create(user=me, url="https://agents.example/hook")
    sent = []
    monkeypatch.setattr("apps.webhooks.tasks.deliver_webhook.delay",
                        lambda hook_id, envelope: sent.append(envelope))

    class Events(list):
        def names(self):
            return [e["event"] for e in sent]

        def of(self, name):
            return [e for e in sent if e["event"] == name]

    return Events()


def tick():
    from apps.method.tasks import tick as run

    run()


@pytest.fixture
def objective(api, me):
    """Liste « BSCP » déclarée objectif actif, avec deux actions ordonnées."""
    project = api.post("/api/projects/", {"name": "BSCP", "objective": "active"},
                       format="json").json()
    first = api.post("/api/tasks/", {"project": project["id"], "title": "Lab SQLi 1",
                                     "sort_order": 1000}, format="json").json()
    second = api.post("/api/tasks/", {"project": project["id"], "title": "Lab SQLi 2",
                                      "sort_order": 2000}, format="json").json()
    return {"project": project, "first": first, "second": second}


def make_slot(api, weekday=0, start="20:30", **extra):
    res = api.post("/api/slots/", {"weekday": weekday, "start_time": start, **extra},
                   format="json")
    assert res.status_code == 201, res.json()
    return res.json()


def occurrences(api, start="2026-10-12", end="2026-10-18"):
    res = api.get(f"/api/slot-occurrences/?start={start}&end={end}")
    assert res.status_code == 200, res.json()
    return res.json()


# ---- Module 36 : créneaux --------------------------------------------------

class TestM36Slots:

    def test_slot_crud_and_owned_objective(self, api, me, clock, django_user_model):
        """Un créneau a jour/heure/durée (25 min par défaut)/objectif/type ;
        l'objectif doit appartenir à l'utilisateur."""
        slot = make_slot(api, weekday=2, start="20:30")
        assert slot["weekday"] == 2
        assert slot["start_time"] == "20:30:00"
        assert slot["duration_minutes"] == 25
        assert slot["kind"] == "work"
        assert slot["project"] is None  # auto

        other = django_user_model.objects.create_user(email="o@x.com", password="x")
        foreign = other.projects.get(is_inbox=True)
        res = api.post("/api/slots/", {"weekday": 0, "start_time": "08:00",
                                       "project": foreign.id}, format="json")
        assert res.status_code == 400

        patched = api.patch(f"/api/slots/{slot['id']}/", {"duration_minutes": 50},
                            format="json")
        assert patched.json()["duration_minutes"] == 50
        assert api.delete(f"/api/slots/{slot['id']}/").status_code == 204

    def test_occurrences_are_wall_clock_in_user_timezone(self, api, me, clock):
        """Lundi 20:30 à Paris = 18:30 UTC ; une occurrence par semaine."""
        make_slot(api, weekday=0, start="20:30")
        occ = occurrences(api)
        assert len(occ) == 1
        assert occ[0]["date"] == "2026-10-12"
        assert occ[0]["start_at"].startswith("2026-10-12T18:30:00")
        assert occ[0]["status"] == "planned"
        # Pas d'occurrence avant la création du créneau (pas de faux « raté »).
        assert occurrences(api, "2026-10-05", "2026-10-11") == []

    def test_next_action_order_and_never_a_proposal(self, api, me, clock, objective):
        """Prochaine action = tâche assignée, sinon 1re tâche ouverte de
        l'objectif (ordre manuel), jamais une proposition non validée."""
        api.post("/api/tasks/", {"project": objective["project"]["id"],
                                 "title": "Proposée", "sort_order": 0, "proposed": True},
                 format="json")
        make_slot(api, weekday=0)  # objectif « auto » → objectif actif
        occ = occurrences(api)[0]
        assert occ["next_action"]["id"] == objective["first"]["id"]

        api.patch(f"/api/slot-occurrences/{occ['id']}/",
                  {"task": objective["second"]["id"]}, format="json")
        assert occurrences(api)[0]["next_action"]["id"] == objective["second"]["id"]

    def test_start_honors_and_launches_10_min_contract(self, api, me, clock, objective):
        """Démarrer honore l'occurrence et lance un focus de 10 min sur la
        prochaine action ; même en retard le jour même."""
        make_slot(api, weekday=0)
        occ = occurrences(api)[0]
        clock.at(12, 21, 30)  # 1 h de retard, créneau déjà raté
        tick()
        assert occurrences(api)[0]["status"] == "missed"

        res = api.post(f"/api/slot-occurrences/{occ['id']}/start/", format="json")
        assert res.status_code == 200, res.json()
        body = res.json()
        assert body["status"] == "honored"
        assert body["task"] == objective["first"]["id"]
        assert body["focus_session"]["planned_seconds"] == 600
        assert body["focus_session"]["task"] == objective["first"]["id"]

    def test_start_refused_too_early_or_another_day(self, api, me, clock):
        make_slot(api, weekday=2)  # mercredi
        occ = occurrences(api)[0]
        res = api.post(f"/api/slot-occurrences/{occ['id']}/start/", format="json")
        assert res.status_code == 400

    def test_relances_once_each_then_missed(self, api, me, clock, events, objective):
        """À l'heure : slot.due ; +15 min : slot.nudge ; fin + 15 min : missed.
        Jamais deux fois le même événement."""
        make_slot(api, weekday=0, start="20:30")
        clock.at(12, 20, 30)
        tick()
        tick()
        assert events.names().count("slot.due") == 1
        due = events.of("slot.due")[0]["data"]
        assert due["next_action"]["title"] == "Lab SQLi 1"

        clock.at(12, 20, 45)
        tick()
        tick()
        assert events.names().count("slot.nudge") == 1

        clock.at(12, 21, 10)  # fin 20:55 + 15 min
        tick()
        tick()
        assert events.names().count("slot.missed") == 1
        assert occurrences(api)[0]["status"] == "missed"

    def test_missed_slot_rolls_into_buffer_then_recovered(self, api, me, clock, objective):
        """Un raté est reporté au prochain tampon libre ; démarrer le tampon le
        marque rattrapé."""
        make_slot(api, weekday=0, start="20:30")
        make_slot(api, weekday=6, start="16:00", kind="buffer")
        clock.at(12, 21, 10)
        tick()
        week = occurrences(api)
        missed = next(o for o in week if o["kind"] == "work")
        buffer = next(o for o in week if o["kind"] == "buffer")
        assert missed["status"] == "missed"
        assert buffer["recovers"] == missed["id"]

        clock.at(18, 16, 0)
        res = api.post(f"/api/slot-occurrences/{buffer['id']}/start/", format="json")
        assert res.status_code == 200
        week = {o["id"]: o for o in occurrences(api)}
        assert week[missed["id"]]["status"] == "recovered"

    def test_unused_buffer_is_free_time(self, api, me, clock):
        make_slot(api, weekday=6, start="16:00", kind="buffer")
        clock.at(18, 17, 0)
        tick()
        assert occurrences(api)[0]["status"] == "free"

    def test_jokers_monthly_quota(self, api, me, clock):
        """2 jokers par mois par défaut ; le 3e est refusé explicitement."""
        for weekday in (0, 2, 5):
            make_slot(api, weekday=weekday)
        week = occurrences(api)
        for occ in week[:2]:
            res = api.post(f"/api/slot-occurrences/{occ['id']}/joker/", format="json")
            assert res.status_code == 200
            assert res.json()["status"] == "excused"
            assert res.json()["excuse_reason"] == "joker"
        third = api.post(f"/api/slot-occurrences/{week[2]['id']}/joker/", format="json")
        assert third.status_code == 400
        assert "joker" in third.json()["detail"].lower()


# ---- Module 37 : couleur du jour & pause -----------------------------------

class TestM37DayColor:

    def test_red_day_excuses_remaining_slots_and_back(self, api, me, clock, events):
        make_slot(api, weekday=0, start="20:30")
        res = api.put("/api/method/day/", {"color": "red"}, format="json")
        assert res.status_code == 200
        occ = occurrences(api)[0]
        assert (occ["status"], occ["excuse_reason"]) == ("excused", "rouge")
        assert "day.color" in events.names()

        api.put("/api/method/day/", {"color": "green"}, format="json")
        assert occurrences(api)[0]["status"] == "planned"

    def test_pause_excuses_and_silences(self, api, me, clock, events):
        make_slot(api, weekday=0, start="20:30")
        api.patch("/api/method/config/", {"pause_until": "2026-10-13"}, format="json")
        clock.at(12, 20, 30)
        tick()
        assert "slot.due" not in events.names()
        occ = occurrences(api)[0]
        assert (occ["status"], occ["excuse_reason"]) == ("excused", "pause")

    def test_today_dashboard(self, api, me, clock, objective, inbox):
        make_slot(api, weekday=0, start="20:30")
        api.put("/api/method/day/", {"color": "orange"}, format="json")
        api.post("/api/tasks/", {"project": inbox.id, "title": "Appeler l'agence",
                                 "due_date": paris(12, 12).isoformat()}, format="json")
        data = api.get("/api/method/today/").json()
        assert data["date"] == "2026-10-12"
        assert data["color"] == "orange"
        assert data["today_count"] == 1
        assert data["today_limit"] == 3
        assert data["jokers_remaining"] == 2
        assert data["level"] == 1
        assert data["occurrences"][0]["next_action"]["title"] == "Lab SQLi 1"


# ---- Module 38 : objectifs & frigo ----------------------------------------

class TestM38Objectives:

    def test_two_active_objectives_max(self, api, me):
        for name in ("BSCP", "Déménagement"):
            res = api.post("/api/projects/", {"name": name, "objective": "active"},
                           format="json")
            assert res.status_code == 201
        third = api.post("/api/projects/", {"name": "Guitare", "objective": "active"},
                         format="json")
        assert third.status_code == 400
        fridge = api.post("/api/projects/", {"name": "Guitare", "objective": "fridge"},
                          format="json")
        assert fridge.status_code == 201

    def test_project_progress(self, api, me):
        project = api.post("/api/projects/", {"name": "Déménagement"}, format="json").json()
        ids = [api.post("/api/tasks/", {"project": project["id"], "title": f"T{i}"},
                        format="json").json()["id"] for i in range(3)]
        api.post(f"/api/tasks/{ids[0]}/complete/")
        api.post(f"/api/tasks/{ids[1]}/wont-do/")
        data = api.get(f"/api/projects/{project['id']}/").json()
        assert (data["tasks_done"], data["tasks_total"]) == (1, 2)


# ---- Module 39 : propositions de l'IA -------------------------------------

class TestM39Proposals:

    def test_proposals_hidden_until_accepted(self, api, me, clock, inbox):
        task = api.post("/api/tasks/", {
            "project": inbox.id, "title": "Créer l'alerte SeLoger", "proposed": True,
            "due_date": paris(12, 18).isoformat(),
        }, format="json", HTTP_X_ACTOR="agent:ram").json()
        assert task["proposed"] is True

        def titles(url):
            data = api.get(url).json()
            items = data if isinstance(data, list) else data.get("results", data)
            return [t["title"] for t in items] if isinstance(items, list) else items

        assert "Créer l'alerte SeLoger" not in titles("/api/tasks/")
        assert "Créer l'alerte SeLoger" not in titles("/api/tasks/?smart=1")
        assert "Créer l'alerte SeLoger" in titles("/api/tasks/?proposed=1")
        today = api.get("/api/tasks/today/?tz=Europe/Paris").json()
        assert "Créer l'alerte SeLoger" not in str(today)

        api.patch(f"/api/tasks/{task['id']}/", {"proposed": False}, format="json")
        assert "Créer l'alerte SeLoger" in titles("/api/tasks/")


# ---- Module 40 : retard & procrastination ---------------------------------

class TestM40Procrastination:

    def test_postpone_counts_only_when_due(self, api, me, clock, inbox):
        future = api.post("/api/tasks/", {"project": inbox.id, "title": "Futur",
                                          "due_date": paris(20, 9).isoformat()},
                          format="json").json()
        api.patch(f"/api/tasks/{future['id']}/", {"due_date": paris(22, 9).isoformat()},
                  format="json")
        assert api.get(f"/api/tasks/{future['id']}/").json()["postpone_count"] == 0

        late = api.post("/api/tasks/", {"project": inbox.id, "title": "En retard",
                                        "due_date": paris(10, 9).isoformat()},
                        format="json").json()
        api.patch(f"/api/tasks/{late['id']}/", {"due_date": paris(13, 9).isoformat()},
                  format="json")
        assert api.get(f"/api/tasks/{late['id']}/").json()["postpone_count"] == 1

        today = api.post("/api/tasks/", {"project": inbox.id, "title": "Aujourd'hui",
                                         "due_date": paris(12, 18).isoformat()},
                         format="json").json()
        api.patch(f"/api/tasks/{today['id']}/", {"due_date": None}, format="json")
        assert api.get(f"/api/tasks/{today['id']}/").json()["postpone_count"] == 1

    def test_third_postpone_blocks_once(self, api, me, clock, inbox, events):
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "Dossier location",
                                        "due_date": paris(12, 9).isoformat()},
                        format="json").json()
        def postpone_to(day):
            api.patch(f"/api/tasks/{task['id']}/", {"due_date": paris(day, 11).isoformat()},
                      format="json")

        for day in (13, 14):  # chaque jour, l'échéance du jour est repoussée
            clock.at(day, 12)
            postpone_to(day + 1)
        assert events.names().count("task.blocked") == 0  # 2 reports seulement
        clock.at(15, 12)
        postpone_to(16)
        assert events.names().count("task.blocked") == 1
        blocked = api.get("/api/tasks/?blocked=1").json()
        assert [t["title"] for t in blocked] == ["Dossier location"]
        clock.at(16, 12)
        postpone_to(17)  # déjà bloquée : pas de nouvel événement
        assert events.names().count("task.blocked") == 1

    def test_diagnose_gives_remedy(self, api, me, clock, inbox, events):
        task = api.post("/api/tasks/", {"project": inbox.id, "title": "Monter le dossier"},
                        format="json").json()
        res = api.post(f"/api/tasks/{task['id']}/diagnose/", {"reason": "too_big"},
                       format="json")
        assert res.status_code == 200
        body = res.json()
        assert "découpe" in body["remedy"].lower()
        assert body["task"]["blocker"] == "too_big"
        assert body["task"]["postpone_count"] == 0
        assert "task.diagnosed" in events.names()

        useless = api.post(f"/api/tasks/{task['id']}/diagnose/", {"reason": "useless"},
                           format="json").json()
        assert useless["task"]["status"] == -1

        bad = api.post(f"/api/tasks/{task['id']}/diagnose/", {"reason": "flemme"},
                       format="json")
        assert bad.status_code == 400


# ---- Module 41 : revue hebdo & niveaux ------------------------------------

class TestM41WeeklyReview:

    def _honor(self, api, occ):
        api.post(f"/api/slot-occurrences/{occ['id']}/start/", format="json")
        api.post("/api/focus-sessions/stop/")

    def test_review_summary(self, api, me, clock, objective, inbox):
        make_slot(api, weekday=0, start="20:30")
        make_slot(api, weekday=2, start="20:30")
        mon, wed = occurrences(api)
        clock.at(12, 20, 30)
        self._honor(api, mon)
        api.post(f"/api/tasks/{objective['first']['id']}/complete/")
        clock.at(14, 21, 30)
        tick()  # mercredi raté
        api.post("/api/tasks/", {"project": inbox.id, "title": "Idée en vrac"},
                 format="json")
        api.post("/api/tasks/", {"project": inbox.id, "title": "Vieille dette",
                                 "due_date": paris(1, 9).isoformat()}, format="json")
        api.post("/api/tasks/", {"project": inbox.id, "title": "Proposée",
                                 "proposed": True}, format="json")

        clock.at(18, 18, 0)
        review = api.get("/api/method/review/").json()
        assert review["week_start"] == "2026-10-12"
        assert review["score"] == {"honored": 1, "decided": 2, "rate": 0.5}
        assert [t["title"] for t in review["completed"]] == ["Lab SQLi 1"]
        assert [t["title"] for t in review["amnesty"]] == ["Vieille dette"]
        assert review["inbox_count"] == 2
        assert review["proposals_count"] == 1
        assert review["suggestion"] == "keep"
        assert review["completed_at"] is None

    def test_review_validation_amnesty_level_idempotent(self, api, me, clock, inbox, events):
        old = api.post("/api/tasks/", {"project": inbox.id, "title": "Vieille dette",
                                       "due_date": paris(1, 9).isoformat()},
                       format="json").json()
        clock.at(18, 18, 0)
        res = api.post("/api/method/review/", {"level": 2}, format="json")
        assert res.status_code == 200
        assert res.json()["completed_at"] is not None
        task = api.get(f"/api/tasks/{old['id']}/").json()
        assert task["due_date"] is None
        assert task["postpone_count"] == 0  # l'amnistie n'est pas un report
        assert api.get("/api/method/config/").json()["level"] == 2
        assert events.names().count("review.completed") == 1

        again = api.post("/api/method/review/", {"level": 3}, format="json")
        assert again.status_code == 200
        assert api.get("/api/method/config/").json()["level"] == 2
        assert events.names().count("review.completed") == 1

    def test_level_suggestion_two_weeks_rule(self, api, me, clock):
        make_slot(api, weekday=0, start="20:30")
        # Deux semaines pleines (lundis 12 et 19).
        for day in (12, 19):
            clock.at(day, 20, 30)
            occ = next(o for o in occurrences(api, "2026-10-12", "2026-10-25")
                       if o["date"] == f"2026-10-{day}")
            self._honor(api, occ)
        clock.at(25, 18, 0)
        assert api.get("/api/method/review/").json()["suggestion"] == "up"

    def test_review_events_upcoming_then_due(self, api, me, clock, events):
        clock.at(18, 16, 0)  # dimanche, revue à 18:00
        tick()
        tick()
        assert events.names().count("review.upcoming") == 1
        assert "review.due" not in events.names()
        clock.at(18, 18, 0)
        tick()
        tick()
        assert events.names().count("review.due") == 1
