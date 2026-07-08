"""Ops — sonde /health/ consommée par les healthchecks Docker (phase 5)."""
import pytest


@pytest.mark.django_db
def test_health_publique_et_verifie_la_base(client):
    """/health/ répond 200 sans auth et fait un aller-retour DB réel."""
    res = client.get("/health/")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
