import secrets

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class EmailUserManager(UserManager):
    """Connexion par email : le username est dérivé de l'email."""

    def create_user(self, email=None, password=None, **extra):
        extra.setdefault("username", email)
        return super().create_user(extra.pop("username"), email, password, **extra)

    def create_superuser(self, username=None, email=None, password=None, **extra):
        email = email or username
        return super().create_superuser(email, email, password, **extra)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=120, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = EmailUserManager()

    def __str__(self):
        return self.email


class UserSettings(models.Model):
    """Préférences globales (module 12.2, 25.3, 26.2 du PRD)."""

    class Theme(models.TextChoices):
        AUTO = "auto"
        LIGHT = "light"
        DARK = "dark"

    class DefaultDue(models.TextChoices):
        NONE = "none"
        TODAY = "today"
        TOMORROW = "tomorrow"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="settings"
    )
    theme = models.CharField(max_length=16, choices=Theme, default=Theme.AUTO)
    theme_preset = models.CharField(max_length=32, blank=True)
    week_start = models.PositiveSmallIntegerField(default=1)  # 0=dim, 1=lun, 6=sam
    reminder_sound = models.CharField(max_length=32, default="default")
    # Visibilité des smart lists par défaut : {"tomorrow": false, ...}
    smart_list_visibility = models.JSONField(default=dict, blank=True)
    # Défauts de création des tâches (module 25.3)
    default_project = models.ForeignKey(
        "projects.Project", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    default_due = models.CharField(
        max_length=16, choices=DefaultDue, default=DefaultDue.NONE
    )
    default_priority = models.PositiveSmallIntegerField(default=0)
    default_reminders = models.JSONField(default=list, blank=True)
    # Options de snooze proposées quand une alerte sonne (module 26.2), en minutes ;
    # les valeurs spéciales "tomorrow_morning" / "next_weekday" sont des chaînes.
    snooze_options = models.JSONField(
        default=list, blank=True
    )
    # NLP de la saisie rapide (module 10.1)
    nlp_enabled = models.BooleanField(default=True)
    nlp_strip_text = models.BooleanField(default=True)
    # Masquage des créneaux horaires inactifs dans les vues calendrier (module M30)
    hidden_hours_start = models.PositiveSmallIntegerField(default=0)  # 0–23
    hidden_hours_end = models.PositiveSmallIntegerField(default=0)    # 0–23 (0 = pas de masquage)
    calendar_layout = models.CharField(max_length=16, default="classic")  # classic|modern
    # Daily review (M26) : heure HH:MM de la notification du matin/soir, null = désactivé
    daily_review_morning = models.TimeField(null=True, blank=True)
    daily_review_evening = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"Settings<{self.user}>"


def generate_api_key():
    return secrets.token_urlsafe(32)


class ApiKey(models.Model):
    """Clé d'API longue durée pour les agents (ex : agent IA Gemini).

    Évite le va-et-vient JWT 7j/180j : l'agent envoie
    `Authorization: Api-Key <token>` sur chaque requête.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="api_keys"
    )
    key = models.CharField(max_length=64, unique=True, default=generate_api_key, db_index=True)
    label = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ApiKey<{self.user} {self.label or self.key[:8]}…>"


class PushSubscription(models.Model):
    """Abonnement Web Push (VAPID) d'un navigateur/appareil pour les rappels."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    endpoint = models.URLField(max_length=512, unique=True)
    p256dh = models.CharField(max_length=255)  # clé publique du client
    auth = models.CharField(max_length=255)    # secret d'authentification
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PushSubscription<{self.user} {self.endpoint[:32]}…>"


class FCMDevice(models.Model):
    """Jeton FCM d'un appareil Android (push mobile). Cf. apps.accounts.fcm."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="fcm_devices"
    )
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FCMDevice<{self.user} {self.token[:16]}…>"
