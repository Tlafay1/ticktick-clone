from rest_framework import serializers

from .models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "color", "parent", "sort_order"]

    def validate_parent(self, parent):
        if parent and parent.user != self.context["request"].user:
            raise serializers.ValidationError("Tag parent inconnu.")
        return parent

    def validate_name(self, name):
        name = name.strip().lstrip("#")
        existing = Tag.objects.filter(user=self.context["request"].user, name=name)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("Un tag porte déjà ce nom.")
        return name
