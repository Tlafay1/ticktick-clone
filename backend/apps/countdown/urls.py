from rest_framework.routers import DefaultRouter
from .views import CountdownViewSet

router = DefaultRouter()
router.register("countdowns", CountdownViewSet, basename="countdown")

urlpatterns = router.urls
