from django.conf import settings
from django.db import models


class Habit(models.Model):
    class Frequency(models.TextChoices):
        DAILY = "daily"
        WEEKLY = "weekly"
        SPECIFIC_DAYS = "specific_days"   # freq_config: {"days": [0,1,2,3,4]}
        INTERVAL = "interval"             # freq_config: {"every": 3}
        WEEKLY_GOAL = "weekly_goal"       # freq_config: {"times": 3}

    class GoalType(models.TextChoices):
        BINARY = "binary"
        NUMERIC = "numeric"

    class CheckInMode(models.TextChoices):
        AUTO = "auto"
        MANUAL = "manual"
        BINARY = "binary"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="habits")
    name = models.CharField(max_length=120)
    icon = models.CharField(max_length=64, blank=True)
    color = models.CharField(max_length=16, blank=True)
    frequency = models.CharField(max_length=16, choices=Frequency, default=Frequency.DAILY)
    freq_config = models.JSONField(default=dict, blank=True)
    goal_type = models.CharField(max_length=16, choices=GoalType, default=GoalType.BINARY)
    goal_value = models.FloatField(default=1.0)
    goal_unit = models.CharField(max_length=32, blank=True)
    motto = models.CharField(max_length=255, blank=True)
    check_in_mode = models.CharField(max_length=16, choices=CheckInMode, default=CheckInMode.BINARY)
    auto_increment = models.FloatField(default=1.0)
    sort_order = models.BigIntegerField(default=0)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.name

    def _completed_dates(self):
        return set(self.checkins.filter(completed=True).values_list("date", flat=True))

    def streak(self, today=None):
        """Streak courant, selon la fréquence de l'habitude.

        - quotidien : jours consécutifs (aujourd'hui non fait ne casse pas
          encore le streak — il est « en cours » jusqu'à minuit) ;
        - jours précis : seuls les jours planifiés comptent, les autres sont
          sautés sans casser la série ;
        - intervalle « tous les N j » : check-ins consécutifs espacés de ≤ N j ;
        - hebdo / objectif hebdo : semaines consécutives atteignant l'objectif
          (la semaine courante, encore en cours, ne casse pas la série).
        """
        from datetime import date, timedelta

        if today is None:
            today = date.today()
        done = self._completed_dates()

        if self.frequency == self.Frequency.INTERVAL:
            every = int((self.freq_config or {}).get("every", 1) or 1)
            dates = sorted(done, reverse=True)
            if not dates or (today - dates[0]).days > every:
                return 0
            streak = 1
            for prev, cur in zip(dates, dates[1:], strict=False):
                if (prev - cur).days <= every:
                    streak += 1
                else:
                    break
            return streak

        if self.frequency in (self.Frequency.WEEKLY, self.Frequency.WEEKLY_GOAL):
            times = int((self.freq_config or {}).get("times", 1) or 1)
            week_start = today - timedelta(days=today.weekday())
            streak = 0
            # Semaine courante : compte si l'objectif est déjà atteint,
            # sinon elle est simplement « en cours » (pas de rupture).
            if sum(1 for d in done if week_start <= d <= today) >= times:
                streak += 1
            week_start -= timedelta(days=7)
            while sum(1 for d in done if week_start <= d < week_start + timedelta(days=7)) >= times:
                streak += 1
                week_start -= timedelta(days=7)
            return streak

        scheduled_days = (self.freq_config or {}).get("days")
        def is_scheduled(day):
            return (
                self.frequency != self.Frequency.SPECIFIC_DAYS
                or not scheduled_days
                or day.weekday() in scheduled_days
            )

        streak = 0
        day = today
        # Aujourd'hui pas encore fait : la série d'hier tient toujours.
        if is_scheduled(day) and day not in done:
            day -= timedelta(days=1)
        while True:
            if not is_scheduled(day):
                day -= timedelta(days=1)
                continue
            if day in done:
                streak += 1
                day -= timedelta(days=1)
            else:
                break
        return streak

    def max_streak(self):
        """Meilleure série historique (mêmes règles de fréquence que streak())."""
        from datetime import timedelta

        done = sorted(self._completed_dates())
        if not done:
            return 0

        if self.frequency == self.Frequency.INTERVAL:
            every = int((self.freq_config or {}).get("every", 1) or 1)
            max_s = cur = 1
            for prev, nxt in zip(done, done[1:], strict=False):
                cur = cur + 1 if (nxt - prev).days <= every else 1
                max_s = max(max_s, cur)
            return max_s

        if self.frequency in (self.Frequency.WEEKLY, self.Frequency.WEEKLY_GOAL):
            times = int((self.freq_config or {}).get("times", 1) or 1)
            per_week = {}
            for d in done:
                per_week[d - timedelta(days=d.weekday())] = per_week.get(d - timedelta(days=d.weekday()), 0) + 1
            weeks = sorted(w for w, n in per_week.items() if n >= times)
            max_s = cur = 1 if weeks else 0
            for prev, nxt in zip(weeks, weeks[1:], strict=False):
                cur = cur + 1 if (nxt - prev).days == 7 else 1
                max_s = max(max_s, cur)
            return max_s

        scheduled_days = (self.freq_config or {}).get("days")
        if self.frequency == self.Frequency.SPECIFIC_DAYS and scheduled_days:
            # Deux jours planifiés se suivent s'il n'y a aucun jour planifié
            # manqué entre eux.
            max_s = cur = 1
            for prev, nxt in zip(done, done[1:], strict=False):
                gap_missed = any(
                    (prev + timedelta(days=i)).weekday() in scheduled_days
                    for i in range(1, (nxt - prev).days)
                )
                cur = 1 if gap_missed else cur + 1
                max_s = max(max_s, cur)
            return max_s

        max_s = cur = 1
        for prev, nxt in zip(done, done[1:], strict=False):
            cur = cur + 1 if (nxt - prev).days == 1 else 1
            max_s = max(max_s, cur)
        return max_s


class HabitReminder(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="reminders")
    time = models.TimeField()
    # Idempotence du dispatch : un rappel part au plus une fois par jour.
    last_sent_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["time"]


class HabitCheckIn(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="checkins")
    date = models.DateField()
    quantity = models.FloatField(default=1.0)
    note = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


HABIT_PRESETS = [
    {"id": "water", "name": "Boire de l'eau", "icon": "💧", "color": "#2196F3",
     "frequency": "daily", "goal_type": "numeric", "goal_value": 8, "goal_unit": "verres",
     "motto": "Reste hydraté·e !"},
    {"id": "exercise", "name": "Exercice physique", "icon": "🏃", "color": "#4CAF50",
     "frequency": "daily", "goal_type": "binary", "goal_value": 1, "goal_unit": "",
     "motto": "Un peu chaque jour !"},
    {"id": "reading", "name": "Lecture", "icon": "📚", "color": "#FF9800",
     "frequency": "daily", "goal_type": "numeric", "goal_value": 20, "goal_unit": "minutes",
     "motto": "Nourris ton esprit"},
    {"id": "meditation", "name": "Méditation", "icon": "🧘", "color": "#9C27B0",
     "frequency": "daily", "goal_type": "numeric", "goal_value": 10, "goal_unit": "minutes",
     "motto": "Sois présent·e"},
    {"id": "sleep", "name": "Sommeil", "icon": "😴", "color": "#3F51B5",
     "frequency": "daily", "goal_type": "numeric", "goal_value": 8, "goal_unit": "heures",
     "motto": "Dors bien !"},
]
