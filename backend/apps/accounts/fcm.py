"""Envoi de notifications push Android via FCM HTTP v1.

Credentials = service account Firebase collé dans la variable d'environnement
`FCM_SERVICE_ACCOUNT_JSON` (aucun fichier sur le serveur). Sans elle, tous les
envois sont ignorés silencieusement (même logique que le Web Push VAPID).
"""
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


def _credentials():
    """(credentials, project_id) depuis l'env, ou (None, None) si FCM désactivé."""
    raw = settings.FCM_SERVICE_ACCOUNT_JSON
    if not raw:
        return None, None
    info = json.loads(raw)
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
    return creds, info["project_id"]


def send_fcm(user, title, body, url="/"):
    """Envoie une notification à tous les appareils FCM de `user`.

    Retourne le nombre d'envois réussis. Purge les jetons expirés (404
    UNREGISTERED). No-op si les credentials ne sont pas configurés.
    """
    creds, project_id = _credentials()
    if creds is None:
        logger.debug("FCM désactivé : FCM_SERVICE_ACCOUNT_JSON absent.")
        return 0

    import requests
    from google.auth.transport.requests import Request

    creds.refresh(Request())
    endpoint = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }
    sent = 0
    for device in user.fcm_devices.all():
        payload = {
            "message": {
                "token": device.token,
                "notification": {"title": title, "body": body},
                "data": {"url": url},
            }
        }
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            sent += 1
        elif resp.status_code == 404:
            device.delete()  # jeton expiré / désenregistré
        else:
            logger.warning("Échec FCM (%s) : %s", resp.status_code, resp.text[:200])
    return sent
