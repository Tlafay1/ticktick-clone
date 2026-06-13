from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserSettings


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def bootstrap_user(sender, instance, created, **kwargs):
    """À l'inscription : crée les settings et la liste Inbox (non supprimable)."""
    if not created:
        return
    from apps.projects.models import Project

    UserSettings.objects.get_or_create(user=instance)
    Project.objects.get_or_create(
        user=instance, is_inbox=True, defaults={"name": "Inbox"}
    )
