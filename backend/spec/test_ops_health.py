"""Ops — sonde /health/, service des médias et CORS des clients natifs."""
import pytest
from django.conf import settings
from django.test import override_settings

# Config de production : une origine web déclarée, donc CORS_ALLOW_ALL_ORIGINS
# retombe à False (cf. settings). C'est dans cette configuration que les clients
# natifs doivent passer.
prod_cors = override_settings(
    CORS_ALLOW_ALL_ORIGINS=False,
    CORS_ALLOWED_ORIGINS=["https://tasks.exemple.com"],
)


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


# Les clients natifs servent leur UI en local : Electron sur un port loopback
# tiré au hasard à chaque lancement (serve-dist.js écoute sur le port 0),
# Capacitor sur https://localhost. Ces origines ne peuvent pas être déclarées
# dans DJANGO_CORS_ALLOWED_ORIGINS — sans quoi la connexion échoue en « erreur
# réseau », le préflight répondant 200 mais sans Access-Control-Allow-Origin.
@prod_cors
@pytest.mark.parametrize(
    "origin",
    [
        "http://127.0.0.1:49531",  # Electron, port aléatoire
        "http://localhost:52014",
        "https://localhost",  # Capacitor Android (androidScheme https par défaut)
        "http://localhost",
    ],
)
def test_cors_autorise_les_clients_natifs(client, origin):
    """Préflight et réponse réelle portent l'en-tête CORS pour les origines locales."""
    pre = client.options(
        "/api/auth/token/",
        HTTP_ORIGIN=origin,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
    )
    assert pre["access-control-allow-origin"] == origin

    res = client.post("/api/auth/token/", {}, HTTP_ORIGIN=origin)
    assert res["access-control-allow-origin"] == origin


@prod_cors
def test_cors_refuse_une_origine_tierce(client):
    """Ouvrir le loopback ne doit pas ouvrir le reste."""
    pre = client.options(
        "/api/auth/token/",
        HTTP_ORIGIN="https://pas-mon-domaine.example",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
    )
    assert "access-control-allow-origin" not in pre
