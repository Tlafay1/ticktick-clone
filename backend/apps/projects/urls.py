from rest_framework.routers import DefaultRouter

from .views import ProjectGroupViewSet, ProjectViewSet, SectionViewSet

router = DefaultRouter()
router.register("project-groups", ProjectGroupViewSet)
router.register("projects", ProjectViewSet)
router.register("sections", SectionViewSet)

urlpatterns = router.urls
