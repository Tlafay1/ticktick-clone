from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    MethodConfigView,
    MethodDayView,
    MethodReviewView,
    MethodTodayView,
    SlotOccurrenceViewSet,
    SlotViewSet,
)

router = DefaultRouter()
router.register("slots", SlotViewSet, basename="slot")
router.register("slot-occurrences", SlotOccurrenceViewSet, basename="slot-occurrence")

urlpatterns = router.urls + [
    path("method/config/", MethodConfigView.as_view(), name="method-config"),
    path("method/today/", MethodTodayView.as_view(), name="method-today"),
    path("method/day/", MethodDayView.as_view(), name="method-day"),
    path("method/review/", MethodReviewView.as_view(), name="method-review"),
]
