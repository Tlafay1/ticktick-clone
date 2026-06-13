import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Channels (WebSocket) sera branché ici au jalon 5.
application = get_asgi_application()
