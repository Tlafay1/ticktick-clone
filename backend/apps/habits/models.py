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

    def streak(self, today=None):
        from datetime import date, timedelta
        if today is None:
            today = date.today()
        streak = 0
        day = today
        while True:
            if self.checkins.filter(date=day, completed=True).exists():
                streak += 1
                day -= timedelta(days=1)
            else:
                break
        return streak

    def max_streak(self):
        dates = sorted(self.checkins.filter(completed=True).values_list("date", flat=True))
        if not dates:
            return 0
        max_s = cur = 1
        for i in range(1, len(dates)):
            if dates[i] - dates[i-1] == __import__('datetime').timedelta(days=1):
                cur += 1
                max_s = max(max_s, cur)
            else:
                cur = 1
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
