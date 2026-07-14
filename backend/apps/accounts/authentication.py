"""Authentification DRF par clé d'API longue durée (header Api-Key)."""

from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
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


class ApiKeyScheme(OpenApiAuthenticationExtension):
    """Documente `Authorization: Api-Key <token>` dans l'OpenAPI."""

    target_class = "apps.accounts.authentication.ApiKeyAuthentication"
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Clé d'API longue durée : `Authorization: Api-Key <token>`.",
        }

