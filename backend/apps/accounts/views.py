from django.conf import settings
from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ApiKey, FCMDevice, PushSubscription, UserSettings
from .serializers import (
    ApiKeySerializer,
    RegisterSerializer,
    UserSerializer,
    UserSettingsSerializer,
)


class RegisterView(generics.CreateAPIView):
    """Inscription ouverte : email + mot de passe, aucune vérification."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=201,
        )


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSettingsSerializer

    def get_object(self):
        obj, _ = UserSettings.objects.get_or_create(user=self.request.user)
        return obj


class ApiKeyViewSet(viewsets.ModelViewSet):
    """Gestion des clés d'API longue durée de l'utilisateur (pour agents/scripts)."""

    serializer_class = ApiKeySerializer

    def get_queryset(self):
        return ApiKey.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PushPublicKeyView(APIView):
    """Expose la clé publique VAPID nécessaire à l'abonnement côté front."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"public_key": settings.VAPID_PUBLIC_KEY})


class PushSubscribeView(APIView):
    """Enregistre (ou met à jour) l'abonnement Web Push du navigateur courant."""

    def post(self, request):
        endpoint = request.data.get("endpoint")
        keys = request.data.get("keys", {})
        if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
            return Response({"detail": "Abonnement incomplet."}, status=400)
        sub, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": keys["p256dh"],
                "auth": keys["auth"],
            },
        )
        return Response({"id": sub.id}, status=201)

    def delete(self, request):
        endpoint = request.data.get("endpoint")
        PushSubscription.objects.filter(
            user=request.user, endpoint=endpoint
        ).delete()
        return Response(status=204)


class FCMTokenView(APIView):
    """Enregistre / retire le jeton FCM de l'appareil Android courant."""

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "Jeton manquant."}, status=400)
        FCMDevice.objects.update_or_create(
            token=token, defaults={"user": request.user}
        )
        return Response(status=201)

    def delete(self, request):
        token = request.data.get("token")
        FCMDevice.objects.filter(user=request.user, token=token).delete()
        return Response(status=204)
