from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as serve_media
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.projects.urls")),
    path("api/", include("apps.tasks.urls")),
    path("api/", include("apps.tags.urls")),
    path("api/", include("apps.calendars.urls")),
    path("api/", include("apps.stats.urls")),
    path("api/", include("apps.habits.urls")),
    path("api/", include("apps.focus.urls")),
    path("api/", include("apps.countdown.urls")),
    path("api/", include("apps.webhooks.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # Médias servis par le backend même en production (DEBUG=0) : nginx proxifie
    # /media/ jusqu'ici. static() ne servait qu'en DEBUG → pièces jointes en 404
    # en prod. En mono-utilisateur self-hosted, servir via Django est acceptable.
    re_path(
        rf"^{settings.MEDIA_URL.lstrip('/')}(?P<path>.*)$",
        serve_media,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
