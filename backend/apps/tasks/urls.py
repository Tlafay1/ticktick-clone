from rest_framework.routers import DefaultRouter

from .views import CheckItemViewSet, CommentViewSet, ReminderViewSet, TaskViewSet, TemplateViewSet

router = DefaultRouter()
router.register("tasks", TaskViewSet)
router.register("check-items", CheckItemViewSet)
router.register("reminders", ReminderViewSet)
router.register("templates", TemplateViewSet)
router.register("comments", CommentViewSet)

urlpatterns = router.urls
