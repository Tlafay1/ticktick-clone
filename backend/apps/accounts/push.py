"""Envoi de notifications Web Push (VAPID) aux abonnements enregistrés."""

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def notify_user(user, title, body, url="/"):
    """Envoie une notification push à tous les appareils abonnés de `user`.

    Sans clés VAPID configurées, l'appel est ignoré silencieusement
    (la fonctionnalité reste optionnelle / désactivable).
    """
    if not (settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY):
        logger.debug("Web Push désactivé : clés VAPID absentes.")
        return 0

    from pywebpush import WebPushException, webpush

    payload = json.dumps({"title": title, "body": body, "url": url})
    sent = 0
    for sub in user.push_subscriptions.all():
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"},
            )
            sent += 1
        except WebPushException as exc:
            # 404/410 : abonnement expiré → on le purge.
            if exc.response is not None and exc.response.status_code in (404, 410):
                sub.delete()
            else:
                logger.warning("Échec Web Push (%s) : %s", sub.endpoint[:32], exc)
    return sent
