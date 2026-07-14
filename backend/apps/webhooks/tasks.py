"""Livraison asynchrone et signée des webhooks."""
import hashlib
import hmac
import json
import urllib.error
import urllib.request

from celery import shared_task
from django.utils import timezone


def sign(secret, body):
    """Signature HMAC-SHA256 hexadécimale du corps (bytes) avec le secret."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@shared_task(
    bind=True,
    max_retries=5,
    retry_backoff=True,       # backoff exponentiel : 1s, 2s, 4s, 8s, 16s…
    retry_backoff_max=600,
    retry_jitter=True,
)
def deliver_webhook(self, webhook_id, envelope):
    """Livre une enveloppe v2 à un webhook, signée et journalisée.

    `envelope` est le dict complet construit par `dispatch.build_envelope`
    (id, event, timestamp, actor, data, changes). En cas d'échec HTTP/réseau,
    la tentative est journalisée puis retentée avec backoff exponentiel.
    """
    from .models import Webhook, WebhookDelivery

    try:
        hook = Webhook.objects.get(pk=webhook_id, is_active=True)
    except Webhook.DoesNotExist:
        return

    event = envelope.get("event", "")
    event_id = envelope.get("id", "")
    body = json.dumps(envelope, default=str).encode()
    request = urllib.request.Request(
        hook.url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ticktick-clone-webhook/2",
            "X-Webhook-Event": event,
            "X-Webhook-Id": event_id,
            "X-Webhook-Signature": f"sha256={sign(hook.secret, body)}",
        },
    )
    delivery = WebhookDelivery(
        webhook=hook, event=event, event_id=event_id, payload=envelope.get("data", {})
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            delivery.status_code = resp.status
            delivery.success = 200 <= resp.status < 300
            delivery.save()
    except urllib.error.HTTPError as exc:
        delivery.status_code = exc.code
        delivery.error = str(exc)[:500]
        delivery.save()
        raise self.retry(exc=exc) from exc
    except Exception as exc:  # réseau : on journalise et on retente
        delivery.error = str(exc)[:500]
        delivery.save()
        raise self.retry(exc=exc) from exc

    Webhook.objects.filter(pk=hook.pk).update(last_triggered_at=timezone.now())
    return delivery.status_code
