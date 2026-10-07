from datetime import date, timedelta

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.actors import get_actor
from apps.projects.views import OwnedModelViewSet
from apps.tasks.models import Task

from . import services
from .models import DayLog, MethodConfig, Slot, SlotOccurrence
from .serializers import (
    DayColorSerializer,
    MethodConfigSerializer,
    ReviewSerializer,
    SlotOccurrenceSerializer,
    SlotSerializer,
)


class SlotViewSet(OwnedModelViewSet):
    """Créneaux récurrents (M36.1). Modifier ou supprimer n'efface que l'avenir."""

    serializer_class = SlotSerializer
    queryset = Slot.objects.all()

    def perform_update(self, serializer):
        serializer.save()
        services.reset_future_occurrences(serializer.instance)

    def perform_destroy(self, instance):
        services.reset_future_occurrences(instance)
        instance.delete()


def _parse_date(value, name):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Date attendue (AAAA-MM-JJ)."}) from None


class SlotOccurrenceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Occurrences datées des créneaux (M36.2) ; PATCH {task} = pré-planifier."""

    serializer_class = SlotOccurrenceSerializer
    queryset = SlotOccurrence.objects.select_related("slot__project", "task", "focus_session")

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    @extend_schema(parameters=[
        OpenApiParameter("start", OpenApiTypes.DATE, description="Défaut : lundi de la semaine."),
        OpenApiParameter("end", OpenApiTypes.DATE, description="Défaut : start + 6 jours."),
    ])
    def list(self, request, *args, **kwargs):
        today = services.local_now(request.user).date()
        start = (_parse_date(request.query_params["start"], "start")
                 if "start" in request.query_params else services.week_start_of(today))
        end = (_parse_date(request.query_params["end"], "end")
               if "end" in request.query_params else start + timedelta(days=6))
        # Le passé ne se matérialise jamais après coup : seul l'avenir est créé.
        if end >= today:
            services.ensure_occurrences(request.user, max(start, today), end)
        qs = self.get_queryset().filter(date__gte=start, date__lte=end)
        return Response(self.get_serializer(qs, many=True).data)

    @extend_schema(request=OpenApiTypes.OBJECT, responses=SlotOccurrenceSerializer)
    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Démarrer en un geste : honore + focus 10 min (ou `minutes`). Corps : task?, minutes?"""
        occurrence = self.get_object()
        task = None
        if request.data.get("task") is not None:
            task = Task.objects.filter(pk=request.data["task"], user=request.user).first()
            if task is None:
                raise ValidationError({"task": "Tâche inconnue."})
        services.start_occurrence(occurrence, task=task, minutes=request.data.get("minutes"),
                                  actor=get_actor(request))
        return Response(self.get_serializer(occurrence).data)

    @extend_schema(request=None, responses=SlotOccurrenceSerializer)
    @action(detail=True, methods=["post"])
    def joker(self, request, pk=None):
        occurrence = services.use_joker(self.get_object())
        return Response(self.get_serializer(occurrence).data)


class MethodConfigView(APIView):
    """Réglages de la méthode (M37.2, M41)."""

    @extend_schema(responses=MethodConfigSerializer)
    def get(self, request):
        return Response(MethodConfigSerializer(MethodConfig.for_user(request.user)).data)

    @extend_schema(request=MethodConfigSerializer, responses=MethodConfigSerializer)
    def patch(self, request):
        config = MethodConfig.for_user(request.user)
        serializer = MethodConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if "pause_until" in serializer.validated_data:
            services.sync_pause(request.user, config)
        return Response(serializer.data)


class MethodTodayView(APIView):
    """Tableau de bord du jour (M37.3) : ce qu'un client ou un agent affiche le matin."""

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        user = request.user
        config = MethodConfig.for_user(user)
        today = services.local_now(user).date()
        services.ensure_occurrences(user, today, today)
        log = DayLog.objects.filter(user=user, date=today).first()
        occurrences = SlotOccurrence.objects.filter(user=user, date=today).select_related(
            "slot__project", "task", "focus_session")
        return Response({
            "date": today.isoformat(),
            "color": log.color if log else None,
            "paused": config.is_paused(today),
            "pause_until": config.pause_until,
            "level": config.level,
            "today_limit": config.today_limit,
            "today_count": services.today_tasks(user).count(),
            "jokers_remaining": services.jokers_remaining(user, today),
            "proposals_count": Task.objects.filter(
                user=user, proposed=True, status=Task.Status.NORMAL, trashed_at__isnull=True,
            ).count(),
            "occurrences": SlotOccurrenceSerializer(occurrences, many=True).data,
        })


class MethodDayView(APIView):
    """Couleur du jour (M37.1) : green | orange | red."""

    @extend_schema(request=DayColorSerializer, responses=OpenApiTypes.OBJECT)
    def put(self, request):
        serializer = DayColorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        day = serializer.validated_data.get("date") or services.local_now(request.user).date()
        color = serializer.validated_data["color"]
        services.set_day_color(request.user, day, color, actor=get_actor(request))
        return Response({"date": day.isoformat(), "color": color})


class MethodReviewView(APIView):
    """Revue hebdo (M41) : GET bilan, POST validation (idempotente)."""

    def _week(self, request, value):
        if value:
            return services.week_start_of(value)
        return services.default_review_week(request.user)

    @extend_schema(parameters=[OpenApiParameter("week", OpenApiTypes.DATE)],
                   responses=OpenApiTypes.OBJECT)
    def get(self, request):
        week = request.query_params.get("week")
        week_start = self._week(request, _parse_date(week, "week") if week else None)
        return Response(services.review_summary(request.user, week_start))

    @extend_schema(request=ReviewSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        week_start = self._week(request, data.get("week"))
        services.complete_review(
            request.user, week_start, level=data.get("level"), amnesty=data["amnesty"],
            notes=data["notes"], actor=get_actor(request),
        )
        return Response(services.review_summary(request.user, week_start),
                        status=status.HTTP_200_OK)
