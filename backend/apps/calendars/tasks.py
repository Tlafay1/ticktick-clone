"""Tâche Celery : rafraîchissement périodique des abonnements ICS."""
from celery import shared_task


@shared_task
def refresh_ics_subscriptions():
    """Réimporte les événements de tous les abonnements (beat horaire)."""
    from .models import CalendarSubscription
    from .sync import refresh_subscription

    total = 0
    for sub in CalendarSubscription.objects.all():
        total += refresh_subscription(sub)
    return total


@shared_task
def refresh_one_subscription(subscription_id):
    """Import initial asynchrone juste après la création d'un abonnement."""
    from .models import CalendarSubscription
    from .sync import refresh_subscription

    try:
        sub = CalendarSubscription.objects.get(pk=subscription_id)
    except CalendarSubscription.DoesNotExist:
        return 0
    return refresh_subscription(sub)
