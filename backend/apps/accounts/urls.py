from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    ApiKeyViewSet,
    MeView,
    PushPublicKeyView,
    PushSubscribeView,
    RegisterView,
    SettingsView,
)

router = DefaultRouter()
router.register("api-keys", ApiKeyViewSet, basename="apikey")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("me/settings/", SettingsView.as_view(), name="settings"),
    path("push/public-key/", PushPublicKeyView.as_view(), name="push-public-key"),
    path("push/subscribe/", PushSubscribeView.as_view(), name="push-subscribe"),
    path("", include(router.urls)),
]
