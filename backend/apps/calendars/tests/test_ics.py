"""ICS read-only (module 4.3) : parsing, dépliage RRULE, refresh, endpoint."""
from datetime import datetime, timedelta, timezone as dt_tz

import pytest

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 7, 12, 12, 0, tzinfo=dt_tz.utc)

# Fixture minimale : un événement horaire simple, un all-day, un récurrent hebdo.
ICS_SAMPLE = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//FR
BEGIN:VEVENT
UID:simple-1
SUMMARY:Réunion d'équipe
LOCATION:Salle B
DTSTART:20260715T090000Z
DTEND:20260715T100000Z
END:VEVENT
BEGIN:VEVENT
UID:allday-1
SUMMARY:Férié
DTSTART;VALUE=DATE:20260714
END:VEVENT
BEGIN:VEVENT
UID:weekly-1
SUMMARY:Cours de sport
DTSTART:20260713T180000Z
DTEND:20260713T190000Z
RRULE:FREQ=WEEKLY;COUNT=4
END:VEVENT
END:VCALENDAR
"""


def test_parse_ics_simple_allday_and_rrule():
    from apps.calendars.sync import parse_ics

    occ = parse_ics(ICS_SAMPLE, now=NOW)
    by_uid = {}
    for o in occ:
        by_uid.setdefault(o["uid"], []).append(o)

    assert len(by_uid["simple-1"]) == 1
    simple = by_uid["simple-1"][0]
    assert simple["title"] == "Réunion d'équipe"
    assert simple["location"] == "Salle B"
    assert simple["is_all_day"] is False
    assert (simple["end"] - simple["start"]) == timedelta(hours=1)

    assert by_uid["allday-1"][0]["is_all_day"] is True

    # RRULE hebdo COUNT=4 → 4 occurrences espacées de 7 jours, durée conservée.
    weekly = sorted(by_uid["weekly-1"], key=lambda o: o["start"])
    assert len(weekly) == 4
    assert weekly[1]["start"] - weekly[0]["start"] == timedelta(days=7)
    assert (weekly[0]["end"] - weekly[0]["start"]) == timedelta(hours=1)


def test_parse_ics_ignores_events_outside_window():
    from apps.calendars.sync import parse_ics

    old = ICS_SAMPLE.replace("20260715T090000Z", "20200101T090000Z")
    occ = parse_ics(old, now=NOW)
    assert not any(o["uid"] == "simple-1" for o in occ)


class _FakeResp:
    status_code = 200
    content = ICS_SAMPLE.encode()

    def raise_for_status(self):
        pass


def _make_sub(user, **kw):
    from apps.calendars.models import CalendarSubscription

    return CalendarSubscription.objects.create(
        user=user, name="Perso", url="https://cal.example/feed.ics", **kw
    )


def test_refresh_subscription_imports_and_stamps(user, monkeypatch):
    from apps.calendars.models import CalendarEvent
    from apps.calendars.sync import refresh_subscription

    sub = _make_sub(user)
    monkeypatch.setattr("requests.get", lambda url, timeout: _FakeResp())
    count = refresh_subscription(sub)
    assert count == 6  # 1 simple + 1 all-day + 4 occurrences hebdo
    assert CalendarEvent.objects.filter(subscription=sub).count() == 6
    sub.refresh_from_db()
    assert sub.last_synced_at is not None

    # Re-refresh : remplacement, pas de doublons.
    assert refresh_subscription(sub) == 6
    assert CalendarEvent.objects.filter(subscription=sub).count() == 6


def test_refresh_keeps_old_events_on_network_error(user, monkeypatch):
    from apps.calendars.models import CalendarEvent
    from apps.calendars.sync import refresh_subscription

    sub = _make_sub(user)
    monkeypatch.setattr("requests.get", lambda url, timeout: _FakeResp())
    refresh_subscription(sub)

    def _boom(url, timeout):
        raise OSError("réseau")

    monkeypatch.setattr("requests.get", _boom)
    assert refresh_subscription(sub) == 0
    assert CalendarEvent.objects.filter(subscription=sub).count() == 6  # conservés


def test_events_endpoint_filters_visibility_and_user(api, user, django_user_model, monkeypatch):
    from apps.calendars.sync import refresh_subscription

    monkeypatch.setattr("requests.get", lambda url, timeout: _FakeResp())
    visible = _make_sub(user)
    hidden = _make_sub(user, is_visible=False)
    refresh_subscription(visible)
    refresh_subscription(hidden)

    other = django_user_model.objects.create_user(email="o@x.com", password="x")
    foreign = _make_sub(other)
    refresh_subscription(foreign)

    resp = api.get("/api/calendar-events/")
    assert resp.status_code == 200
    data = resp.json()
    # Seuls les événements de l'abonnement visible du user courant.
    assert len(data) == 6
    assert all(e["subscription"] == visible.id for e in data)
    assert data[0]["calendar_name"] == "Perso"

    # Filtre de plage : seule la réunion du 15 juillet matche.
    resp = api.get("/api/calendar-events/?start=2026-07-15T00:00:00Z&end=2026-07-15T23:59:59Z")
    assert [e["uid"] for e in resp.json()] == ["simple-1"]


def test_subscription_create_schedules_initial_import(api, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "apps.calendars.tasks.refresh_one_subscription.delay",
        lambda sid: calls.append(sid),
    )
    resp = api.post(
        "/api/calendar-subscriptions/",
        {"name": "Équipe", "url": "https://cal.example/x.ics"},
        format="json",
    )
    assert resp.status_code == 201
    assert calls == [resp.json()["id"]]
