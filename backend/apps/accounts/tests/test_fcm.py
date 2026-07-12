"""FCM (push Android) : endpoint d'enregistrement + envoi via service account env."""
import pytest

pytestmark = pytest.mark.django_db


class _FakeCreds:
    token = "ya29.fake"

    def refresh(self, request):
        pass


class _FakeResp:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


# --- endpoint d'enregistrement ---------------------------------------------

def test_register_and_unregister_fcm_token(api, user):
    from apps.accounts.models import FCMDevice

    assert api.post("/api/push/fcm-token/", {"token": "dev-abc"}, format="json").status_code == 201
    assert FCMDevice.objects.filter(user=user, token="dev-abc").count() == 1
    # ré-enregistrer le même jeton ne duplique pas.
    api.post("/api/push/fcm-token/", {"token": "dev-abc"}, format="json")
    assert FCMDevice.objects.filter(token="dev-abc").count() == 1

    assert api.delete("/api/push/fcm-token/", {"token": "dev-abc"}, format="json").status_code == 204
    assert FCMDevice.objects.filter(token="dev-abc").count() == 0


def test_register_requires_token(api):
    assert api.post("/api/push/fcm-token/", {}, format="json").status_code == 400


# --- envoi ------------------------------------------------------------------

def test_send_fcm_noop_without_credentials(settings, user):
    from apps.accounts.fcm import send_fcm
    from apps.accounts.models import FCMDevice

    settings.FCM_SERVICE_ACCOUNT_JSON = ""
    FCMDevice.objects.create(user=user, token="t1")
    assert send_fcm(user, "T", "B") == 0


def test_send_fcm_posts_to_each_device(settings, user, monkeypatch):
    from apps.accounts import fcm
    from apps.accounts.models import FCMDevice

    settings.FCM_SERVICE_ACCOUNT_JSON = '{"project_id": "proj-1"}'
    FCMDevice.objects.create(user=user, token="t1")
    FCMDevice.objects.create(user=user, token="t2")

    monkeypatch.setattr(fcm, "_credentials", lambda: (_FakeCreds(), "proj-1"))
    calls = []
    monkeypatch.setattr("requests.post", lambda url, **kw: calls.append((url, kw)) or _FakeResp(200))

    assert fcm.send_fcm(user, "Titre", "Corps", url="/task/1") == 2
    assert len(calls) == 2
    url, kw = calls[0]
    assert url == "https://fcm.googleapis.com/v1/projects/proj-1/messages:send"
    assert kw["headers"]["Authorization"] == "Bearer ya29.fake"
    assert kw["json"]["message"]["notification"] == {"title": "Titre", "body": "Corps"}


def test_send_fcm_purges_unregistered_token(settings, user, monkeypatch):
    from apps.accounts import fcm
    from apps.accounts.models import FCMDevice

    settings.FCM_SERVICE_ACCOUNT_JSON = '{"project_id": "proj-1"}'
    FCMDevice.objects.create(user=user, token="stale")
    monkeypatch.setattr(fcm, "_credentials", lambda: (_FakeCreds(), "proj-1"))
    monkeypatch.setattr("requests.post", lambda url, **kw: _FakeResp(404, "UNREGISTERED"))

    assert fcm.send_fcm(user, "T", "B") == 0
    assert FCMDevice.objects.filter(user=user).count() == 0
