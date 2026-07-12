from rest_framework.routers import DefaultRouter

from .views import CalendarEventViewSet, CalendarSubscriptionViewSet

router = DefaultRouter()
router.register("calendar-subscriptions", CalendarSubscriptionViewSet)
router.register("calendar-events", CalendarEventViewSet, basename="calendar-event")

urlpatterns = router.urls
