"""Consumer WebSocket : auth JWT et diffusion aux connexions du même user."""
import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.sync.routing import websocket_urlpatterns

# On route directement vers le consumer (sans AuthMiddlewareStack, redondant
# ici puisque le consumer fait sa propre auth JWT).
application = URLRouter(websocket_urlpatterns)


@pytest.fixture(autouse=True)
def _in_memory_channels(settings):
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(email="o@x.com", password="x")


async def _connect(token):
    communicator = WebsocketCommunicator(application, f"/ws/tasks/?token={token}")
    connected, _ = await communicator.connect()
    return communicator, connected


@pytest.mark.django_db
async def test_rejects_missing_or_garbage_token():
    communicator, connected = await _connect("garbage")
    assert connected is False
    await communicator.disconnect()


@pytest.mark.django_db
async def test_rejects_refresh_token(user):
    """Un refresh token passait UntypedToken puis crashait — doit fermer proprement."""
    refresh = str(RefreshToken.for_user(user))
    communicator, connected = await _connect(refresh)
    assert connected is False
    await communicator.disconnect()


@pytest.mark.django_db
async def test_accepts_access_token(user):
    token = str(AccessToken.for_user(user))
    communicator, connected = await _connect(token)
    assert connected is True
    await communicator.disconnect()


@pytest.mark.django_db
async def test_broadcasts_to_same_user_but_not_sender(user):
    token = str(AccessToken.for_user(user))
    c1, ok1 = await _connect(token)
    c2, ok2 = await _connect(token)
    assert ok1 and ok2

    await c1.send_json_to({"type": "task.created", "task": {"id": 7}})
    received = await c2.receive_json_from(timeout=1)
    assert received["task"]["id"] == 7
    # L'émetteur ne se reçoit pas lui-même.
    assert await c1.receive_nothing() is True

    await c1.disconnect()
    await c2.disconnect()


@pytest.mark.django_db
async def test_two_different_users_are_isolated(user, other_user):
    c1, _ = await _connect(str(AccessToken.for_user(user)))
    c2, _ = await _connect(str(AccessToken.for_user(other_user)))

    await c1.send_json_to({"type": "task.updated", "task": {"id": 1}})
    # L'autre utilisateur (groupe distinct) ne reçoit rien.
    assert await c2.receive_nothing() is True

    await c1.disconnect()
    await c2.disconnect()
