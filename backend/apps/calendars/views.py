from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.views import OwnedModelViewSet

from .models import CalendarEvent, CalendarSubscription
from .serializers import CalendarEventSerializer, CalendarSubscriptionSerializer


class CalendarSubscriptionViewSet(OwnedModelViewSet):
    serializer_class = CalendarSubscriptionSerializer
    queryset = CalendarSubscription.objects.all()

    def perform_create(self, serializer):
        super().perform_create(serializer)
        # Import initial asynchrone (le worker fait le fetch réseau).
        from .tasks import refresh_one_subscription

        refresh_one_subscription.delay(serializer.instance.id)

    @action(detail=True, methods=["post"])
    def refresh(self, request, pk=None):
        """Réimporte immédiatement (synchrone) les événements de l'abonnement."""
        from .sync import refresh_subscription

        count = refresh_subscription(self.get_object())
        return Response({"imported": count})


class CalendarEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Événements ICS importés, lecture seule. Filtres ?start=&end= (ISO)."""

    serializer_class = CalendarEventSerializer

    def get_queryset(self):
        qs = CalendarEvent.objects.filter(
            subscription__user=self.request.user,
            subscription__is_visible=True,
        ).select_related("subscription")
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            qs = qs.filter(start__gte=start)
        if end:
            qs = qs.filter(start__lte=end)
        return qs
