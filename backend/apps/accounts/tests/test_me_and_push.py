"""Profil /api/me/, endpoints Web Push et notify_user (chaîne push)."""
import pytest

pytestmark = pytest.mark.django_db


# --- /api/me/ ---------------------------------------------------------------

def test_me_returns_profile_with_settings(api, user):
    resp = api.get("/api/me/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == user.email
    assert "settings" in data


def test_me_patch_updates_display_name_but_not_email(api):
    resp = api.patch("/api/me/", {"display_name": "Tim", "email": "hack@x.com"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Tim"
    # email est en lecture seule : inchangé.
    assert resp.json()["email"] != "hack@x.com"


def test_me_requires_auth():
    from rest_framework.test import APIClient

    assert APIClient().get("/api/me/").status_code in (401, 403)


# --- Web Push endpoints -----------------------------------------------------

def test_push_public_key_is_public(api):
    resp = api.get("/api/push/public-key/")
    assert resp.status_code == 200
    assert "public_key" in resp.json()


def test_push_subscribe_requires_complete_payload(api):
    assert api.post("/api/push/subscribe/", {"endpoint": "x"}, format="json").status_code == 400


def test_push_subscribe_then_delete(api, user):
    from apps.accounts.models import PushSubscription

    payload = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "k", "auth": "a"}}
    assert api.post("/api/push/subscribe/", payload, format="json").status_code == 201
    assert PushSubscription.objects.filter(user=user).count() == 1
    # Idempotent : ré-abonner le même endpoint ne duplique pas.
    api.post("/api/push/subscribe/", payload, format="json")
    assert PushSubscription.objects.filter(user=user).count() == 1

    assert api.delete("/api/push/subscribe/", {"endpoint": payload["endpoint"]}, format="json").status_code == 204
    assert PushSubscription.objects.filter(user=user).count() == 0


# --- notify_user ------------------------------------------------------------

def test_notify_user_noop_without_vapid_keys(settings, user):
    from apps.accounts.models import PushSubscription
    from apps.accounts.push import notify_user

    settings.VAPID_PRIVATE_KEY = ""
    settings.VAPID_PUBLIC_KEY = ""
    PushSubscription.objects.create(user=user, endpoint="e", p256dh="k", auth="a")
    assert notify_user(user, "Titre", "Corps") == 0


def test_notify_user_sends_to_each_subscription(settings, user, monkeypatch):
    from apps.accounts.models import PushSubscription
    from apps.accounts import push

    settings.VAPID_PRIVATE_KEY = "priv"
    settings.VAPID_PUBLIC_KEY = "pub"
    PushSubscription.objects.create(user=user, endpoint="e1", p256dh="k", auth="a")
    PushSubscription.objects.create(user=user, endpoint="e2", p256dh="k", auth="a")

    calls = []
    monkeypatch.setattr("pywebpush.webpush", lambda **kw: calls.append(kw))
    assert push.notify_user(user, "T", "B", url="/task/1") == 2
    assert len(calls) == 2


def test_notify_user_purges_expired_subscription(settings, user, monkeypatch):
    from apps.accounts.models import PushSubscription
    from apps.accounts import push

    settings.VAPID_PRIVATE_KEY = "priv"
    settings.VAPID_PUBLIC_KEY = "pub"
    PushSubscription.objects.create(user=user, endpoint="gone", p256dh="k", auth="a")

    class FakeResp:
        status_code = 410

    from pywebpush import WebPushException

    def _raise(**kw):
        raise WebPushException("expired", response=FakeResp())

    monkeypatch.setattr("pywebpush.webpush", _raise)
    assert push.notify_user(user, "T", "B") == 0
    # L'abonnement 410 est purgé.
    assert PushSubscription.objects.filter(user=user).count() == 0
