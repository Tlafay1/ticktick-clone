from rest_framework import serializers

from .models import Webhook, WebhookDelivery


class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = [
            "id", "url", "events", "secret", "is_active",
            "created_at", "last_triggered_at",
        ]
        # `secret` est généré côté serveur mais renvoyé (une fois) pour que le
        # récepteur puisse vérifier la signature HMAC.
        read_only_fields = ["id", "secret", "created_at", "last_triggered_at"]

    def validate_events(self, events):
        unknown = [e for e in events if e not in Webhook.EVENTS]
        if unknown:
            raise serializers.ValidationError(
                f"Événements inconnus : {', '.join(unknown)}. "
                f"Valides : {', '.join(Webhook.EVENTS)}."
            )
        return events


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = ["id", "event", "status_code", "success", "error", "created_at"]
