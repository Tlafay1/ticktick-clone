"""Ops — sonde /health/ et service des médias en production."""
import pytest
from django.conf import settings


@pytest.mark.django_db
def test_health_publique_et_verifie_la_base(client):
    """/health/ répond 200 sans auth et fait un aller-retour DB réel."""
    res = client.get("/health/")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_media_servi_par_le_backend(client):
    """/media/ est servi indépendamment de DEBUG (pièces jointes en prod).

    static() ne servait qu'en DEBUG → 404 derrière nginx en production.
    """
    media_root = settings.MEDIA_ROOT
    media_root.mkdir(parents=True, exist_ok=True)
    probe = media_root / "probe_ops.txt"
    probe.write_text("ok")
    try:
        res = client.get("/media/probe_ops.txt")
        assert res.status_code == 200
        assert b"ok" in b"".join(res.streaming_content)
    finally:
        probe.unlink(missing_ok=True)
