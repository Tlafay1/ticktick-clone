from apps.projects.views import OwnedModelViewSet

from .models import CalendarSubscription
from .serializers import CalendarSubscriptionSerializer


class CalendarSubscriptionViewSet(OwnedModelViewSet):
    serializer_class = CalendarSubscriptionSerializer
    queryset = CalendarSubscription.objects.all()
