import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from apps.accounts.actors import get_actor
from apps.webhooks.dispatch import emit

from . import vault
from .models import JournalEntry, JournalMoment
from .serializers import (
    JournalEntrySerializer,
    JournalMomentSerializer,
    JournalWriteSerializer,
)


class VaultUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Vault Obsidian indisponible."
    default_code = "vault_unavailable"


def _tz(name):
    """ZoneInfo demandé, UTC si absent ou invalide."""
    if not name:
        return datetime.timezone.utc
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return datetime.timezone.utc


_KIND_SECTIONS = [
    (JournalMoment.Kind.POSITIF, "Moments positifs"),
    (JournalMoment.Kind.NEGATIF, "Moments négatifs"),
    (JournalMoment.Kind.ANECDOTE, "Anecdotes"),
    (JournalMoment.Kind.RESSENTI, "Ressentis"),
]

# Champ du payload → kind de moment.
KIND_BY_FIELD = {
    "highlights": JournalMoment.Kind.POSITIF,
    "lows": JournalMoment.Kind.NEGATIF,
    "anecdotes": JournalMoment.Kind.ANECDOTE,
    "feelings": JournalMoment.Kind.RESSENTI,
}


def render_section(entry):
    """Rend la section markdown complète du jour (format contrôlé)."""
    tz = _tz(entry.tz)
    lines = [f"## {settings.JOURNAL_HEADING}"]
    if entry.mood:
        stamp = ""
        if entry.mood_noted_at:
            stamp = f" *({timezone.localtime(entry.mood_noted_at, tz):%H:%M})*"
        lines.append(f"**Ressenti général** : {entry.mood}{stamp}")
    moments = list(entry.moments.all())
    for kind, title in _KIND_SECTIONS:
        group = [m for m in moments if m.kind == kind]
        if not group:
            continue
        lines += ["", f"### {title}"]
        lines += [
            f"- **{timezone.localtime(m.noted_at, tz):%H:%M}** — {m.text}"
            for m in group
        ]
    actors = list(dict.fromkeys([m.actor for m in moments]
                                + ([entry.mood_actor] if entry.mood else [])))
    if actors:
        lines += ["", f"*Tenu par {', '.join(actors)}*"]
    return "\n".join(lines) + "\n"


def sync_note(entry):
    """Re-rend la section et l'écrit dans la daily note. → (markdown, chemin)."""
    section = render_section(entry)
    try:
        rel = vault.upsert_journal_section(entry.date, section)
    except vault.VaultUnavailable as exc:
        raise VaultUnavailableError(str(exc)) from exc
    return section, rel


class JournalEntryViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Journal intime tenu par un agent dans la daily note Obsidian.

    `POST` fusionne (merge incrémental) : les listes ajoutent des moments,
    `mood` pose/remplace le ressenti général. La section `## Journal` de la
    daily note est re-rendue en entier à chaque écriture.
    """

    serializer_class = JournalEntrySerializer
    queryset = JournalEntry.objects.all()
    lookup_field = "date"
    lookup_value_regex = r"\d{4}-\d{2}-\d{2}"

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        entry = self.get_object()
        data = self.get_serializer(entry).data
        data["rendered_markdown"] = render_section(entry)
        return Response(data)

    @extend_schema(request=JournalWriteSerializer, responses=JournalEntrySerializer)
    def create(self, request):
        ser = JournalWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payload = ser.validated_data
        actor = get_actor(request)
        tz_name = payload.get("tz")
        date = payload.get("date") or timezone.localtime(
            timezone.now(), _tz(tz_name)
        ).date()

        with transaction.atomic():
            entry, _ = JournalEntry.objects.get_or_create(
                user=request.user, date=date, defaults={"tz": tz_name or "UTC"}
            )
            if tz_name:
                entry.tz = tz_name
            if "mood" in payload:
                entry.mood = payload["mood"]
                entry.mood_noted_at = timezone.now()
                entry.mood_actor = actor
            entry.save()
            for field, kind in KIND_BY_FIELD.items():
                for text in payload.get(field, []):
                    JournalMoment.objects.create(
                        entry=entry, kind=kind, text=text, actor=actor
                    )
            section, rel = sync_note(entry)

        data = JournalEntrySerializer(entry).data
        data["rendered_markdown"] = section
        data["note_path"] = rel
        emit(request.user, "journal.updated", data, actor=actor)
        return Response(data, status=status.HTTP_201_CREATED)


class JournalMomentViewSet(
    mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """Correction d'un moment déjà noté (texte/type) ou suppression."""

    serializer_class = JournalMomentSerializer
    queryset = JournalMoment.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(entry__user=self.request.user)

    def _resync(self, entry):
        sync_note(entry)
        data = JournalEntrySerializer(entry).data
        emit(self.request.user, "journal.updated", data, actor=get_actor(self.request))

    def perform_update(self, serializer):
        with transaction.atomic():
            serializer.save()
            self._resync(serializer.instance.entry)

    def perform_destroy(self, instance):
        with transaction.atomic():
            entry = instance.entry
            instance.delete()
            self._resync(entry)
