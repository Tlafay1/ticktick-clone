from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserSettings
from .serializers import RegisterSerializer, UserSerializer, UserSettingsSerializer


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
