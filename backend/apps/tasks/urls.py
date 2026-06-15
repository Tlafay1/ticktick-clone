from rest_framework.routers import DefaultRouter

from .views import (
    AttachmentViewSet, CheckItemViewSet, CommentViewSet,
    ReminderViewSet, SearchHistoryViewSet, TaskViewSet, TemplateViewSet,
)

router = DefaultRouter()
router.register("tasks", TaskViewSet)
router.register("check-items", CheckItemViewSet)
router.register("reminders", ReminderViewSet)
router.register("templates", TemplateViewSet)
router.register("comments", CommentViewSet)
router.register("attachments", AttachmentViewSet)
router.register("search-history", SearchHistoryViewSet, basename="searchhistory")

urlpatterns = router.urls
