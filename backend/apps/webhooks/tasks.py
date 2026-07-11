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


@shared_task(bind=True, max_retries=3, default_retry_delay=15)
def deliver_webhook(self, webhook_id, event, payload):
    from .models import Webhook, WebhookDelivery

    try:
        hook = Webhook.objects.get(pk=webhook_id, is_active=True)
    except Webhook.DoesNotExist:
        return

    body = json.dumps({"event": event, "data": payload}, default=str).encode()
    request = urllib.request.Request(
        hook.url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ticktick-clone-webhook/1",
            "X-Webhook-Event": event,
            "X-Webhook-Signature": f"sha256={sign(hook.secret, body)}",
        },
    )
    delivery = WebhookDelivery(webhook=hook, event=event, payload=payload)
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
