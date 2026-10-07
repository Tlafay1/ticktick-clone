"""Abonnements explicites aux tâches → reçoivent aussi les événements de la méthode.

Un webhook créé avec une liste d'événements (pas « tous ») ne verrait jamais les
événements de la méthode (API 0.3.0), et l'interface ne permet pas de modifier la
liste d'un webhook existant : il faudrait le recréer, donc changer de secret côté
consommateur. Les consommateurs des tâches (l'écosystème d'agents) les reçoivent
d'office ; ils ignorent ce qu'ils ne savent pas traiter.
"""
from django.db import migrations

EVENEMENTS_METHODE = [
    "slot.due", "slot.nudge", "slot.missed", "slot.started", "day.color",
    "review.upcoming", "review.due", "review.completed", "task.blocked", "task.diagnosed",
]


def etendre(apps, schema_editor):
    Webhook = apps.get_model("webhooks", "Webhook")
    for hook in Webhook.objects.all():
        events = list(hook.events or [])
        if events and any(str(e).startswith("task.") for e in events):
            hook.events = events + [e for e in EVENEMENTS_METHODE if e not in events]
            hook.save(update_fields=["events"])


class Migration(migrations.Migration):
    dependencies = [("webhooks", "0002_webhookdelivery_event_id")]

    operations = [migrations.RunPython(etendre, migrations.RunPython.noop)]
