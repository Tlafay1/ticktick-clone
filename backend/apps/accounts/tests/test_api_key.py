"""Tests de l'authentification par clé d'API longue durée (agents)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ApiKey


@pytest.mark.django_db
def test_api_key_authenticates(user, inbox):
    key = ApiKey.objects.create(user=user, label="agent")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {key.key}")

    resp = client.get("/api/tasks/")
    assert resp.status_code == 200

    # L'usage est horodaté.
    key.refresh_from_db()
    assert key.last_used_at is not None


@pytest.mark.django_db
def test_api_key_create_via_endpoint_then_use(api, user, inbox):
    # L'utilisateur crée une clé (auth JWT/session via la fixture `api`).
    created = api.post("/api/api-keys/", {"label": "gemini"}, format="json")
    assert created.status_code == 201
    token = created.data["key"]
    assert token

    # La clé pilote ensuite l'API sans JWT.
    agent = APIClient()
    agent.credentials(HTTP_AUTHORIZATION=f"Api-Key {token}")
    assert agent.post(
        "/api/tasks/", {"title": "via agent", "project": inbox.id}, format="json"
    ).status_code == 201


@pytest.mark.django_db
def test_invalid_api_key_rejected():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Api-Key totally-bogus")
    assert client.get("/api/tasks/").status_code in (401, 403)
