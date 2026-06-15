from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from apps.projects.views import OwnedModelViewSet
from .models import Habit, HabitCheckIn, HabitReminder, HABIT_PRESETS
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
        # auto-complete: if quantity >= goal_value, mark completed
        if habit.goal_type == Habit.GoalType.BINARY:
            checkin.completed = True
        elif checkin.quantity >= habit.goal_value:
            checkin.completed = True
        checkin.save()
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
