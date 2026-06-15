from rest_framework.routers import DefaultRouter
from .views import FocusSessionViewSet

router = DefaultRouter()
router.register("focus-sessions", FocusSessionViewSet, basename="focussession")

urlpatterns = router.urls
