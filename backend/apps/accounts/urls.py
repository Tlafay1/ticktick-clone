from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    MeView,
    PushPublicKeyView,
    PushSubscribeView,
    RegisterView,
    SettingsView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("me/settings/", SettingsView.as_view(), name="settings"),
    path("push/public-key/", PushPublicKeyView.as_view(), name="push-public-key"),
    path("push/subscribe/", PushSubscribeView.as_view(), name="push-subscribe"),
]
