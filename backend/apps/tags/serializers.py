from rest_framework import serializers

from .models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'
        read_only_fields = ('user',)

    def validate_name(self, value):
        return value.lstrip('#').strip()

    def validate_parent(self, parent):
        if parent and parent.user != self.context['request'].user:
            raise serializers.ValidationError("Le tag parent n'appartient pas à cet utilisateur.")
        return parent

    def validate(self, data):
        user = self.context['request'].user
        name = data.get('name', getattr(self.instance, 'name', None))
        qs = Tag.objects.filter(user=user, name=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({"name": "Un tag avec ce nom existe déjà."})
        return data
