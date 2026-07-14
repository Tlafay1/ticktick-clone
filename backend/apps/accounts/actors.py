"""Attribution d'acteur des écritures API (en-tête `X-Actor`).

Un agent externe s'identifie en envoyant `X-Actor: agent:<slug>` sur ses
requêtes d'écriture ; sans en-tête, l'écriture est attribuée à `user`.
Valeur libre (non authentifiée) : elle sert à distinguer l'origine des
modifications dans les réponses et les payloads webhook, pas à sécuriser.
"""

DEFAULT_ACTOR = "user"
ACTOR_MAX_LENGTH = 64


def get_actor(request):
    """Acteur de la requête : `X-Actor` nettoyé, ou `user` par défaut."""
    value = (request.headers.get("X-Actor") or "").strip()
    return value[:ACTOR_MAX_LENGTH] or DEFAULT_ACTOR
