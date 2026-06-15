from rest_framework.routers import DefaultRouter

from .views import CalendarSubscriptionViewSet

router = DefaultRouter()
router.register("calendar-subscriptions", CalendarSubscriptionViewSet)

urlpatterns = router.urls
