from rest_framework import serializers
from .models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'
        read_only_fields = ('user',)

    def validate_parent(self, parent):
        """Ensure parent tag belongs to the same user."""
        if parent and parent.user != self.context['request'].user:
            raise serializers.ValidationError("Parent tag must belong to the same user.")
        return parent

    def validate_name(self, name):
        """Ensure tag name is not empty."""
        if not name or not name.strip():
            raise serializers.ValidationError("Tag name cannot be empty.")
        return name
