"""Unités habitudes : agrégation des logs numériques et calcul de streak."""
from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.django_db


def _make(api, **kwargs):
    payload = {"name": "H", "goal_type": "binary", **kwargs}
    return api.post("/api/habits/", payload, format="json").json()


def test_numeric_day_completes_only_when_daily_sum_reaches_goal(api):
    """8 verres = 8 logs de 1 : le jour est atteint à la somme, pas au log isolé."""
    habit = _make(api, goal_type="numeric", goal_value=8, goal_unit="verres")
    today = date.today().isoformat()
    for _ in range(7):
        api.post(f"/api/habits/{habit['id']}/checkins/", {"date": today, "quantity": 1}, format="json")
    checkins = api.get(f"/api/habits/{habit['id']}/checkins/?date={today}").json()
    assert all(c["completed"] is False for c in checkins)  # 7 < 8

    last = api.post(
        f"/api/habits/{habit['id']}/checkins/", {"date": today, "quantity": 1}, format="json"
    ).json()
    assert last["completed"] is True  # 8 == 8
    checkins = api.get(f"/api/habits/{habit['id']}/checkins/?date={today}").json()
    assert all(c["completed"] is True for c in checkins)


def test_numeric_single_log_meeting_goal_completes(api):
    habit = _make(api, goal_type="numeric", goal_value=2000, goal_unit="ml")
    today = date.today().isoformat()
    resp = api.post(
        f"/api/habits/{habit['id']}/checkins/", {"date": today, "quantity": 2000}, format="json"
    )
    assert resp.json()["completed"] is True


def test_streak_counts_consecutive_completed_days(api):
    """Streak courant = jours consécutifs terminés en remontant depuis aujourd'hui."""
    from apps.habits.models import Habit

    habit = _make(api)
    obj = Habit.objects.get(pk=habit["id"])
    today = date.today()
    for offset in (0, 1, 2):  # aujourd'hui, hier, avant-hier
        api.post(
            f"/api/habits/{habit['id']}/checkins/",
            {"date": (today - timedelta(days=offset)).isoformat(), "quantity": 1},
            format="json",
        )
    assert obj.streak(today=today) == 3

    detail = api.get(f"/api/habits/{habit['id']}/").json()
    assert detail["streak"] == 3


def test_streak_breaks_on_gap(api):
    from apps.habits.models import Habit

    habit = _make(api)
    obj = Habit.objects.get(pk=habit["id"])
    today = date.today()
    # aujourd'hui et il y a 2 jours (trou hier) → streak courant = 1.
    for offset in (0, 2):
        api.post(
            f"/api/habits/{habit['id']}/checkins/",
            {"date": (today - timedelta(days=offset)).isoformat(), "quantity": 1},
            format="json",
        )
    assert obj.streak(today=today) == 1
    assert obj.max_streak() == 1


def test_max_streak_finds_longest_run(api):
    from apps.habits.models import Habit

    habit = _make(api)
    obj = Habit.objects.get(pk=habit["id"])
    base = date(2026, 3, 1)
    # série de 3 jours, trou, série de 2 jours
    for offset in (0, 1, 2, 5, 6):
        api.post(
            f"/api/habits/{habit['id']}/checkins/",
            {"date": (base + timedelta(days=offset)).isoformat(), "quantity": 1},
            format="json",
        )
    assert obj.max_streak() == 3
