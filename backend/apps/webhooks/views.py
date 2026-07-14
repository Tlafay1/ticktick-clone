from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.views import OwnedModelViewSet

from .models import Webhook
from .serializers import WebhookDeliverySerializer, WebhookSerializer


class WebhookViewSet(OwnedModelViewSet):
    """CRUD des webhooks du user + ping de test + journal de livraisons."""

    serializer_class = WebhookSerializer
    queryset = Webhook.objects.all()

    @action(detail=True, methods=["post"])
    def ping(self, request, pk=None):
        """Envoie un événement de test au webhook (vérifier le récepteur)."""
        from .dispatch import build_envelope
        from .tasks import deliver_webhook

        hook = self.get_object()
        envelope = build_envelope("ping", {"message": "pong"})
        deliver_webhook.delay(hook.id, envelope)
        return Response({"detail": "Ping envoyé."})

    @action(detail=True, methods=["get"])
    def deliveries(self, request, pk=None):
        """Historique des dernières tentatives de livraison (debug)."""
        hook = self.get_object()
        qs = hook.deliveries.all()[:50]
        return Response(WebhookDeliverySerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def events(self, request):
        """Catalogue des événements disponibles."""
        return Response({"events": Webhook.EVENTS})
