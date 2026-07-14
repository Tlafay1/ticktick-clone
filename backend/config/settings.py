"""Réglages Django du clone TickTick.

Philosophie : système mono-utilisateur, simple et ouvert. Pas de captcha,
pas de rate-limiting, pas de vérification d'email.
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "insecure-dev-key-change-me-in-production"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
# Toujours accepter le loopback : les healthchecks Docker sondent /health/
# via 127.0.0.1, quel que soit le domaine public configuré.
ALLOWED_HOSTS += [h for h in ("localhost", "127.0.0.1") if h not in ALLOWED_HOSTS]


def _env_list(name):
    """Lit une variable d'env CSV en liste (vide si absente)."""
    raw = os.environ.get(name, "").strip()
    return [v.strip() for v in raw.split(",") if v.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Tiers
    "rest_framework",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # Apps
    "apps.accounts",
    "apps.projects",
    "apps.tasks",
    "apps.tags",
    "apps.calendars",
    "apps.stats",
    "apps.habits",
    "apps.focus",
    "apps.countdown",
    "apps.sync",
    "apps.webhooks",
    "channels",
]

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [(REDIS_HOST, REDIS_PORT)]},
    }
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise sert les fichiers statiques (admin, Swagger) en prod sans nginx.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "ticktick"),
        "USER": os.environ.get("POSTGRES_USER", "ticktick"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "ticktick"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

# Système ouvert : aucune contrainte de complexité de mot de passe.
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.ApiKeyAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    # Mono-utilisateur self-hosted : des durées longues évitent les
    # déconnexions intempestives sur mobile/desktop.
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=180),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "TickTick Clone API",
    "DESCRIPTION": "API REST ouverte du clone TickTick self-hosted.",
    "VERSION": "0.2.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# CORS : ouvert en dev ; en prod, restreint aux origines déclarées.
CORS_ALLOWED_ORIGINS = _env_list("DJANGO_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = DEBUG or not CORS_ALLOWED_ORIGINS

# CSRF / sécurité derrière le reverse-proxy Dokploy (Traefik) en TLS.
CSRF_TRUSTED_ORIGINS = _env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # Traefik termine déjà le TLS ; redirection optionnelle via env.
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "0") == "1"
    # La sonde Docker interroge /health/ en HTTP loopback : ne pas la rediriger.
    SECURE_REDIRECT_EXEMPT = [r"^health/$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Celery : déclenchement des rappels et purge de corbeille.
REDIS_URL = os.environ.get("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "dispatch-due-reminders": {
        "task": "apps.tasks.tasks.dispatch_due_reminders",
        "schedule": 60.0,  # toutes les minutes
    },
    "dispatch-habit-reminders": {
        "task": "apps.habits.tasks.dispatch_habit_reminders",
        "schedule": 60.0,  # toutes les minutes
    },
    "purge-expired-trash": {
        "task": "apps.tasks.tasks.purge_expired_trash",
        "schedule": 3600.0,  # toutes les heures
    },
    "refresh-ics-subscriptions": {
        "task": "apps.calendars.tasks.refresh_ics_subscriptions",
        "schedule": 3600.0,  # toutes les heures
    },
}

# Web Push (VAPID) — notifications de rappel vers le PWA.
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_ADMIN_EMAIL = os.environ.get("VAPID_ADMIN_EMAIL", "admin@example.com")

# FCM (push Android) — service account collé dans UNE variable d'env (aucun
# fichier google-services.json côté serveur). Vide = FCM désactivé (no-op).
FCM_SERVICE_ACCOUNT_JSON = os.environ.get("FCM_SERVICE_ACCOUNT_JSON", "")
