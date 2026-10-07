"""Cas limites des occurrences de créneaux (compléments à spec/test_jalon9_methode.py)."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from apps.method.models import SlotOccurrence
from apps.method.tasks import tick

pytestmark = pytest.mark.django_db

PARIS = ZoneInfo("Europe/Paris")


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        now = datetime(2026, 10, 12, 10, 0, tzinfo=PARIS)  # lundi

        def at(self, day, hour, minute=0):
            self.now = datetime(2026, 10, day, hour, minute, tzinfo=PARIS)

    c = Clock()
    monkeypatch.setattr("django.utils.timezone.now", lambda: c.now)
    return c


@pytest.fixture(autouse=True)
def paris_user(user):
    user.settings.timezone = "Europe/Paris"
    user.settings.save()


def test_slot_created_after_its_hour_is_not_missed_today(api, user, clock):
    """Créer à 21 h le créneau de 20 h 30 ne doit pas compter un raté le jour même."""
    clock.at(12, 21, 0)
    api.post("/api/slots/", {"weekday": 0, "start_time": "20:30"}, format="json")
    clock.at(12, 23, 0)
    tick()
    assert not SlotOccurrence.objects.filter(user=user, date="2026-10-12").exists()


def test_editing_slot_keeps_history_and_reschedules_future(api, user, clock):
    slot = api.post("/api/slots/", {"weekday": 0, "start_time": "20:30"}, format="json").json()
    week = api.get("/api/slot-occurrences/?start=2026-10-12&end=2026-10-19").json()
    clock.at(12, 20, 30)
    api.post(f"/api/slot-occurrences/{week[0]['id']}/start/", format="json")

    api.patch(f"/api/slots/{slot['id']}/", {"start_time": "21:00"}, format="json")
    after = api.get("/api/slot-occurrences/?start=2026-10-12&end=2026-10-19").json()
    assert after[0]["id"] == week[0]["id"] and after[0]["status"] == "honored"
    assert after[1]["start_at"].startswith("2026-10-19T19:00:00")  # 21:00 Paris


def test_start_attaches_running_focus_session(api, user, clock):
    api.post("/api/slots/", {"weekday": 0, "start_time": "20:30"}, format="json")
    occ = api.get("/api/slot-occurrences/").json()[0]
    clock.at(12, 20, 25)
    running = api.post("/api/focus-sessions/start/", {"planned_seconds": 1500},
                       format="json").json()
    started = api.post(f"/api/slot-occurrences/{occ['id']}/start/", format="json").json()
    assert started["focus_session"]["id"] == running["id"]


def test_lifting_pause_restores_planned(api, user, clock):
    api.post("/api/slots/", {"weekday": 0, "start_time": "20:30"}, format="json")
    api.patch("/api/method/config/", {"pause_until": "2026-10-20"}, format="json")
    assert api.get("/api/slot-occurrences/").json()[0]["status"] == "excused"
    api.patch("/api/method/config/", {"pause_until": None}, format="json")
    assert api.get("/api/slot-occurrences/").json()[0]["status"] == "planned"


def test_review_pending_from_upcoming_until_done(api, user, clock):
    api.post("/api/slots/", {"weekday": 0, "start_time": "20:30"}, format="json")
    assert api.get("/api/method/today/").json()["review_pending"] is False
    clock.at(18, 16, 0)  # dimanche, 2 h avant la revue
    assert api.get("/api/method/today/").json()["review_pending"] is True
    clock.at(19, 9, 0)  # lundi : la revue d'hier attend toujours
    assert api.get("/api/method/today/").json()["review_pending"] is True
    api.post("/api/method/review/", {}, format="json")
    assert api.get("/api/method/today/").json()["review_pending"] is False


def test_new_user_has_no_pending_review(api, user, clock):
    clock.at(19, 9, 0)
    api.post("/api/slots/", {"weekday": 2, "start_time": "20:30"}, format="json")
    assert api.get("/api/method/today/").json()["review_pending"] is False
