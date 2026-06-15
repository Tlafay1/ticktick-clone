from django.conf import settings
from django.db import models


class FocusSession(models.Model):
    class Mode(models.TextChoices):
        POMODORO = "pomodoro"
        STOPWATCH = "stopwatch"

    class SessionType(models.TextChoices):
        WORK = "work"
        SHORT_BREAK = "short_break"
        LONG_BREAK = "long_break"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="focus_sessions")
    task = models.ForeignKey(
        "tasks.Task", null=True, blank=True, on_delete=models.SET_NULL, related_name="focus_sessions"
    )
    mode = models.CharField(max_length=16, choices=Mode, default=Mode.POMODORO)
    session_type = models.CharField(max_length=16, choices=SessionType, default=SessionType.WORK)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-start_at"]

    def __str__(self):
        return f"Focus<{self.user} {self.start_at}>"
