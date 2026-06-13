import pytest
from rest_framework.test import APIClient


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email="tim@example.com", password="secret"
    )


@pytest.fixture
def inbox(user):
    return user.projects.get(is_inbox=True)


@pytest.fixture
def api(user):
    client = APIClient()
    client.force_authenticate(user)
    return client
