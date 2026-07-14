"""Point d'entrée unique pour émettre un événement vers les webhooks du user."""
import uuid

from django.utils import timezone


def build_envelope(event, payload, actor="user", changes=None):
    """Enveloppe webhook v2 : snapshot + métadonnées d'événement.

    - `id` : identifiant d'événement stable (idempotence côté consommateur).
    - `timestamp` : ISO 8601 avec fuseau.
    - `actor` : origine de l'écriture ("user", "agent:<slug>"…).
    - `data` : snapshot de l'entité. `event`/`data` restent présents pour
      compatibilité avec les récepteurs existants.
    - `changes` : diff {champ: {old, new}} sur les événements *.updated.
    """
    envelope = {
        "id": str(uuid.uuid4()),
        "event": event,
        "timestamp": timezone.now().isoformat(),
        "actor": actor,
        "data": payload,
    }
    if changes:
        envelope["changes"] = changes
    return envelope


def emit(user, event, payload, actor="user", changes=None):
    """Enfile une livraison pour chaque webhook actif du user abonné à `event`.

    Sûr à appeler dans le chemin de requête : chaque livraison part en tâche
    Celery (asynchrone, avec retries et backoff). No-op si l'utilisateur n'a
    aucun webhook. L'enveloppe (dont l'id d'événement) est construite une fois
    ici, donc identique à travers les retries.
    """
    from .models import Webhook
    from .tasks import deliver_webhook

    hooks = Webhook.objects.filter(user=user, is_active=True)
    if not hooks:
        return
    envelope = build_envelope(event, payload, actor=actor, changes=changes)
    for hook in hooks:
        if hook.matches(event):
            deliver_webhook.delay(hook.id, envelope)
