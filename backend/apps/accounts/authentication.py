"""Authentification DRF par clé d'API longue durée (header Api-Key)."""

from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import ApiKey


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """Authentifie via `Authorization: Api-Key <token>`.

    Pensé pour les agents (IA, scripts) : pas de refresh, un seul jeton stable.
    """

    keyword = "Api-Key"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].decode().lower() != self.keyword.lower():
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("En-tête Api-Key mal formé.")
        token = header[1].decode()
        try:
            api_key = ApiKey.objects.select_related("user").get(key=token)
        except ApiKey.DoesNotExist:
            raise exceptions.AuthenticationFailed("Clé d'API invalide.")
        # Suivi d'usage (sans bloquer la requête).
        ApiKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
        return (api_key.user, api_key)
