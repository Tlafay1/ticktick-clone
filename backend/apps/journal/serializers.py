from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from .models import JournalEntry, JournalMoment


class JournalMomentSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalMoment
        fields = ["id", "kind", "text", "noted_at", "actor"]
        read_only_fields = ["noted_at", "actor"]


class JournalEntrySerializer(serializers.ModelSerializer):
    moments = JournalMomentSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = ["id", "date", "tz", "mood", "mood_noted_at", "moments", "updated_at"]


class JournalWriteSerializer(serializers.Serializer):
    """Payload de complétion incrémentale d'une journée.

    Chaque appel fusionne : `mood` remplace le ressenti général, les listes
    ajoutent des moments horodatés. Au moins un champ doit être fourni.
    """

    date = serializers.DateField(required=False)
    tz = serializers.CharField(required=False)
    mood = serializers.CharField(required=False, max_length=300)
    highlights = serializers.ListField(
        child=serializers.CharField(), required=False, help_text="Moments positifs."
    )
    lows = serializers.ListField(
        child=serializers.CharField(), required=False, help_text="Moments négatifs."
    )
    anecdotes = serializers.ListField(child=serializers.CharField(), required=False)
    feelings = serializers.ListField(
        child=serializers.CharField(), required=False, help_text="Ressentis détaillés."
    )

    CONTENT_FIELDS = ["mood", "highlights", "lows", "anecdotes", "feelings"]

    def validate_tz(self, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError(f"Fuseau horaire inconnu : {value}")
        return value

    def validate(self, attrs):
        if not any(attrs.get(field) for field in self.CONTENT_FIELDS):
            raise serializers.ValidationError(
                "Fournir au moins un contenu : mood, highlights, lows, anecdotes ou feelings."
            )
        return attrs
