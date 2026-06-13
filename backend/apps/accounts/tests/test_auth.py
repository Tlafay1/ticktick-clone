import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_register_creates_user_settings_and_inbox():
    client = APIClient()
    res = client.post(
        "/api/auth/register/",
        {"email": "new@example.com", "password": "pw", "display_name": "Tim"},
    )
    assert res.status_code == 201
    assert res.data["access"] and res.data["refresh"]
    assert res.data["user"]["settings"]["nlp_enabled"] is True

    # Connexion JWT par email
    res = client.post("/api/auth/token/", {"email": "new@example.com", "password": "pw"})
    assert res.status_code == 200

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    projects = client.get("/api/projects/").data
    assert len(projects) == 1 and projects[0]["is_inbox"] is True


def test_register_duplicate_email_rejected(user):
    res = APIClient().post(
        "/api/auth/register/", {"email": "tim@example.com", "password": "x"}
    )
    assert res.status_code == 400


def test_me_and_settings_update(api):
    res = api.patch("/api/me/settings/", {"theme": "dark", "week_start": 0})
    assert res.status_code == 200
    fresh = api.get("/api/me/settings/").data
    assert fresh["theme"] == "dark"
    assert fresh["week_start"] == 0
