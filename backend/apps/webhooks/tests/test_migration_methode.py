"""Migration 0003 : les abonnements explicites aux tâches reçoivent la méthode."""
import importlib

import pytest
from django.apps import apps

pytestmark = pytest.mark.django_db

migration = importlib.import_module("apps.webhooks.migrations.0003_evenements_methode")


def test_un_abonnement_aux_taches_recoit_la_methode_les_autres_non(user):
    from apps.webhooks.models import Webhook

    taches = Webhook.objects.create(user=user, url="https://agents/hook", events=["task.created"])
    tous = Webhook.objects.create(user=user, url="https://n8n/hook", events=[])
    projets = Webhook.objects.create(user=user, url="https://x/hook", events=["project.created"])

    migration.etendre(apps, None)

    taches.refresh_from_db()
    assert "slot.due" in taches.events and "review.upcoming" in taches.events
    assert taches.events[0] == "task.created"
    tous.refresh_from_db()
    assert tous.events == []  # « tous » reste « tous »
    projets.refresh_from_db()
    assert projets.events == ["project.created"]
