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


# ── Streaks selon la fréquence (module 6) ────────────────────────────────────


def _habit_obj(user, **kwargs):
    from apps.habits.models import Habit

    return Habit.objects.create(user=user, name="H", **kwargs)


def _check(habit, day):
    from apps.habits.models import HabitCheckIn

    HabitCheckIn.objects.create(habit=habit, date=day, completed=True)


def test_daily_streak_today_pending_does_not_break(user):
    """Hier et avant-hier faits, aujourd'hui pas encore : streak = 2 (en cours)."""
    habit = _habit_obj(user)
    today = date.today()
    _check(habit, today - timedelta(days=1))
    _check(habit, today - timedelta(days=2))
    assert habit.streak(today=today) == 2


def test_specific_days_skips_unscheduled_days(user):
    """Lun-mer-ven : le mardi/jeudi non planifiés ne cassent pas la série."""
    habit = _habit_obj(user, frequency="specific_days", freq_config={"days": [0, 2, 4]})
    monday = date(2026, 7, 6)   # lundi
    _check(habit, monday)                       # lun
    _check(habit, monday + timedelta(days=2))   # mer
    _check(habit, monday + timedelta(days=4))   # ven
    # Dimanche suivant (non planifié) : la série des 3 jours planifiés tient.
    assert habit.streak(today=monday + timedelta(days=6)) == 3
    assert habit.max_streak() == 3


def test_specific_days_missed_scheduled_day_breaks(user):
    habit = _habit_obj(user, frequency="specific_days", freq_config={"days": [0, 2, 4]})
    monday = date(2026, 7, 6)
    _check(habit, monday)                       # lun fait
    # mercredi manqué
    _check(habit, monday + timedelta(days=4))   # ven fait
    assert habit.streak(today=monday + timedelta(days=4)) == 1
    assert habit.max_streak() == 1


def test_interval_streak_allows_gaps_up_to_n_days(user):
    habit = _habit_obj(user, frequency="interval", freq_config={"every": 3})
    today = date.today()
    _check(habit, today - timedelta(days=6))
    _check(habit, today - timedelta(days=3))
    _check(habit, today)
    assert habit.streak(today=today) == 3
    assert habit.max_streak() == 3
    # Un trou > 3 jours casse.
    habit2 = _habit_obj(user, frequency="interval", freq_config={"every": 3})
    _check(habit2, today - timedelta(days=5))
    _check(habit2, today)
    assert habit2.streak(today=today) == 1


def test_weekly_goal_counts_consecutive_achieved_weeks(user):
    """3×/semaine : 2 semaines pleines + semaine courante en cours → streak 2."""
    habit = _habit_obj(user, frequency="weekly_goal", freq_config={"times": 3})
    today = date(2026, 7, 8)  # mercredi
    week_start = today - timedelta(days=today.weekday())
    for w in (1, 2):  # deux semaines précédentes complètes
        for d in (0, 2, 4):
            _check(habit, week_start - timedelta(days=7 * w) + timedelta(days=d))
    _check(habit, week_start)  # semaine courante : 1/3 seulement (en cours)
    assert habit.streak(today=today) == 2
    # Semaine courante atteinte → 3.
    _check(habit, week_start + timedelta(days=1))
    _check(habit, week_start + timedelta(days=2))
    assert habit.streak(today=today) == 3
    assert habit.max_streak() == 3
