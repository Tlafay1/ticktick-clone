from django.conf import settings
from django.db import models

from apps.accounts.actors import ACTOR_MAX_LENGTH, DEFAULT_ACTOR


class JournalEntry(models.Model):
    """Journal intime d'une journée, tenu au fil de l'eau par un agent.

    Source de vérité de la section `## Journal` de la daily note Obsidian :
    chaque écriture re-rend la section complète depuis cet état, ce qui permet
    à l'agent de compléter la journée en plusieurs appels (un moment à midi,
    le ressenti global au coucher) sans append-only.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="journal_entries"
    )
    date = models.DateField()
    # Fuseau de la journée : fixe l'affichage des heures dans la note, quel que
    # soit le moment du re-rendu.
    tz = models.CharField(max_length=64, default="UTC")
    mood = models.CharField("ressenti général", max_length=300, blank=True)
    mood_noted_at = models.DateTimeField(null=True, blank=True)
    mood_actor = models.CharField(max_length=ACTOR_MAX_LENGTH, default=DEFAULT_ACTOR)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=("user", "date"), name="unique_journal_day")
        ]

    def __str__(self):
        return f"Journal {self.date}"


class JournalMoment(models.Model):
    """Un moment raconté dans la journée (horodaté, attribué à son acteur)."""

    class Kind(models.TextChoices):
        POSITIF = "positif", "Moment positif"
        NEGATIF = "negatif", "Moment négatif"
        ANECDOTE = "anecdote", "Anecdote"
        RESSENTI = "ressenti", "Ressenti"

    entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name="moments"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    text = models.TextField()
    noted_at = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=ACTOR_MAX_LENGTH, default=DEFAULT_ACTOR)

    class Meta:
        ordering = ["noted_at", "id"]

    def __str__(self):
        return f"{self.kind}: {self.text[:40]}"
