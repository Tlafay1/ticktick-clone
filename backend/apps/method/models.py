"""Méthode d'organisation (modules 36 à 41) : créneaux, couleur du jour, revue.

Les heures sont « murales » : elles s'interprètent dans le fuseau de
l'utilisateur (UserSettings.timezone), jamais en UTC serveur.
"""
from datetime import time, timedelta

from django.conf import settings
from django.db import models


class MethodConfig(models.Model):
    """Réglages de la méthode (le reste — contrat 10 min, relance 15 min… — est fixe)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="method_config"
    )
    level = models.PositiveSmallIntegerField(default=1)
    jokers_per_month = models.PositiveSmallIntegerField(default=2)
    today_limit = models.PositiveSmallIntegerField(default=3)
    review_weekday = models.PositiveSmallIntegerField(default=6)  # lundi = 0
    review_time = models.TimeField(default=time(18, 0))
    # Pause (maladie, gros événement) : jusqu'à cette date incluse, rien ne compte.
    pause_until = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"MethodConfig<{self.user}>"

    @classmethod
    def for_user(cls, user):
        return cls.objects.get_or_create(user=user)[0]

    def is_paused(self, day):
        return self.pause_until is not None and day <= self.pause_until


class Slot(models.Model):
    """Créneau récurrent : un rendez-vous fixe avec un objectif (M36.1)."""

    class Kind(models.TextChoices):
        WORK = "work", "Travail"
        BUFFER = "buffer", "Tampon"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="slots")
    weekday = models.PositiveSmallIntegerField()  # lundi = 0
    start_time = models.TimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=25)
    # Objectif travaillé ; vide = « auto » (objectif actif le mieux classé).
    project = models.ForeignKey(
        "projects.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="slots"
    )
    kind = models.CharField(max_length=8, choices=Kind, default=Kind.WORK)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["weekday", "start_time", "id"]

    def __str__(self):
        return f"Slot<{self.user} j{self.weekday} {self.start_time}>"


class SlotOccurrence(models.Model):
    """Occurrence datée d'un créneau : c'est elle qu'on honore, rate ou excuse (M36.2)."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Prévu"
        HONORED = "honored", "Honoré"
        MISSED = "missed", "Raté"
        EXCUSED = "excused", "Excusé"
        RECOVERED = "recovered", "Rattrapé"
        FREE = "free", "Libre"  # tampon sans rien à rattraper

    class Excuse(models.TextChoices):
        JOKER = "joker", "Joker"
        ROUGE = "rouge", "Journée rouge"
        PAUSE = "pause", "Pause"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="slot_occurrences"
    )
    # SET_NULL : supprimer un créneau ne réécrit pas l'historique (score passé).
    slot = models.ForeignKey(Slot, null=True, on_delete=models.SET_NULL, related_name="occurrences")
    date = models.DateField()
    start_at = models.DateTimeField()
    # Dénormalisés depuis le créneau : l'historique reste lisible s'il change.
    duration_minutes = models.PositiveSmallIntegerField(default=25)
    kind = models.CharField(max_length=8, choices=Slot.Kind, default=Slot.Kind.WORK)
    status = models.CharField(max_length=10, choices=Status, default=Status.PLANNED)
    excuse_reason = models.CharField(max_length=8, choices=Excuse, blank=True)
    # Tâche assignée (pré-planifiée en revue) puis effectivement travaillée.
    task = models.ForeignKey(
        "tasks.Task", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    started_at = models.DateTimeField(null=True, blank=True)
    focus_session = models.ForeignKey(
        "focus.FocusSession", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Tampon : occurrence ratée qu'il rattrape (report automatique, M36.6).
    recovers = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="recovered_by"
    )
    due_sent_at = models.DateTimeField(null=True, blank=True)
    nudge_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["start_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=("slot", "date"), name="unique_occurrence_per_slot_day"),
        ]

    def __str__(self):
        return f"SlotOccurrence<{self.date} {self.status}>"

    @property
    def end_at(self):
        return self.start_at + timedelta(minutes=self.duration_minutes)


class DayLog(models.Model):
    """Couleur du jour (M37.1) : vert normal, orange version minimale, rouge repos."""

    class Color(models.TextChoices):
        GREEN = "green", "Vert"
        ORANGE = "orange", "Orange"
        RED = "red", "Rouge"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="day_logs")
    date = models.DateField()
    color = models.CharField(max_length=8, choices=Color)

    class Meta:
        ordering = ["-date"]
        constraints = [models.UniqueConstraint(fields=("user", "date"), name="unique_daylog_per_day")]

    def __str__(self):
        return f"DayLog<{self.date} {self.color}>"


class WeeklyReview(models.Model):
    """Revue d'une semaine (lundi → dimanche) : rendez-vous, puis bilan figé (M41)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_reviews"
    )
    week_start = models.DateField()
    upcoming_sent_at = models.DateTimeField(null=True, blank=True)
    due_sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rate = models.FloatField(null=True, blank=True)
    level_before = models.PositiveSmallIntegerField(null=True, blank=True)
    level_after = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-week_start"]
        constraints = [
            models.UniqueConstraint(fields=("user", "week_start"), name="unique_review_per_week"),
        ]

    def __str__(self):
        return f"WeeklyReview<{self.user} {self.week_start}>"
