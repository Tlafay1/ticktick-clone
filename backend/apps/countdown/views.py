from apps.projects.views import OwnedModelViewSet
from .models import Countdown
from .serializers import CountdownSerializer


class CountdownViewSet(OwnedModelViewSet):
    serializer_class = CountdownSerializer

    def get_queryset(self):
        return Countdown.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
