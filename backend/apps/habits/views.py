from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.actors import get_actor
from apps.projects.views import OwnedModelViewSet
from .models import Habit, HABIT_PRESETS
from .serializers import HabitSerializer, HabitCheckInSerializer, HabitReminderSerializer


class HabitViewSet(OwnedModelViewSet):
    serializer_class = HabitSerializer

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user).prefetch_related("reminders", "checkins")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="checkins")
    def checkins(self, request, pk=None):
        habit = self.get_object()
        if request.method == "GET":
            qs = habit.checkins.all()
            date_filter = request.query_params.get("date")
            if date_filter:
                qs = qs.filter(date=date_filter)
            return Response(HabitCheckInSerializer(qs, many=True).data)
        serializer = HabitCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        checkin = serializer.save(habit=habit)
        if habit.goal_type == Habit.GoalType.BINARY:
            checkin.completed = True
            checkin.save(update_fields=["completed"])
        else:
            # Objectif numérique : le JOUR est atteint quand la SOMME des logs
            # du jour ≥ goal (8 verres = 8 check-ins de 1), pas chaque log isolé.
            from django.db.models import Sum

            day_total = habit.checkins.filter(date=checkin.date).aggregate(
                s=Sum("quantity")
            )["s"] or 0
            day_done = day_total >= habit.goal_value
            habit.checkins.filter(date=checkin.date).update(completed=day_done)
            checkin.refresh_from_db()
        from apps.webhooks.dispatch import emit

        emit(request.user, "habit.checkin", {
            "habit": habit.id,
            "habit_name": habit.name,
            "checkin": HabitCheckInSerializer(checkin).data,
        }, actor=get_actor(request))
        return Response(HabitCheckInSerializer(checkin).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="reminders")
    def habit_reminders(self, request, pk=None):
        habit = self.get_object()
        if request.method == "GET":
            return Response(HabitReminderSerializer(habit.reminders.all(), many=True).data)
        serializer = HabitReminderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reminder = serializer.save(habit=habit)
        return Response(HabitReminderSerializer(reminder).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="presets")
    def presets(self, request):
        return Response(HABIT_PRESETS)
