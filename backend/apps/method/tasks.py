"""Tick minute de la méthode : relances, ratés, tampons, rendez-vous de revue."""
import logging

from celery import shared_task
from django.contrib.auth import get_user_model

from .services import tick_user

logger = logging.getLogger(__name__)


@shared_task
def tick():
    """Idempotent : chaque transition horodate ce qu'elle a fait (due/nudge/revue)."""
    for user in get_user_model().objects.filter(is_active=True):
        try:
            tick_user(user)
        except Exception:  # un utilisateur en erreur ne bloque pas les autres
            logger.exception("Tick méthode en échec pour %s", user.pk)
