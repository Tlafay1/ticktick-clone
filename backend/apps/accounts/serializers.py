from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserSettings

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "display_name"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        exclude = ["id", "user"]


class UserSerializer(serializers.ModelSerializer):
    settings = UserSettingsSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "date_joined", "settings"]
        read_only_fields = ["id", "email", "date_joined"]
