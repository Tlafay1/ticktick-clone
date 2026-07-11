"""Point d'entrée unique pour émettre un événement vers les webhooks du user."""


def emit(user, event, payload):
    """Enfile une livraison pour chaque webhook actif du user abonné à `event`.

    Sûr à appeler dans le chemin de requête : chaque livraison part en tâche
    Celery (asynchrone, avec retries). No-op si l'utilisateur n'a aucun webhook.
    """
    from .models import Webhook
    from .tasks import deliver_webhook

    hooks = Webhook.objects.filter(user=user, is_active=True)
    for hook in hooks:
        if hook.matches(event):
            deliver_webhook.delay(hook.id, event, payload)
