from rest_framework.routers import DefaultRouter

from .views import JournalEntryViewSet, JournalMomentViewSet

router = DefaultRouter()
router.register("journal/entries", JournalEntryViewSet, basename="journal-entry")
router.register("journal/moments", JournalMomentViewSet, basename="journal-moment")

urlpatterns = router.urls
