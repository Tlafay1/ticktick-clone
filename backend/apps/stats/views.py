from datetime import date, timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tasks.models import Task


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def heatmap(request):
    """Nombre de tâches terminées par jour pour une année donnée."""
    year = int(request.query_params.get("year", timezone.now().year))
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    tasks = Task.objects.filter(
        user=request.user,
        status=Task.Status.COMPLETED,
        completed_at__date__gte=start,
        completed_at__date__lte=end,
    ).values_list("completed_at", flat=True)

    counts = {}
    for completed_at in tasks:
        day = completed_at.date().isoformat()
        counts[day] = counts.get(day, 0) + 1

    return Response(counts)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary(request):
    """Vue d'ensemble : tâches du jour, en retard, par liste, meilleures heures."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    user_tasks = Task.objects.filter(user=request.user, trashed_at__isnull=True)

    completed_today = user_tasks.filter(
        status=Task.Status.COMPLETED,
        completed_at__gte=today_start,
        completed_at__lte=today_end,
    ).count()

    overdue = user_tasks.filter(
        status=Task.Status.NORMAL,
        due_date__lt=today_start,
    ).count()

    # Distribution par liste (aujourd'hui + prochains 7 jours actives)
    by_list = {}
    for task in user_tasks.filter(status=Task.Status.NORMAL).select_related("project"):
        name = task.project.name if task.project else "Inbox"
        by_list[name] = by_list.get(name, 0) + 1

    # Meilleures heures : heures avec le plus de complétions sur 30 jours
    thirty_days_ago = now - timedelta(days=30)
    hour_counts = {}
    for completed_at in user_tasks.filter(
        status=Task.Status.COMPLETED,
        completed_at__gte=thirty_days_ago,
    ).values_list("completed_at", flat=True):
        h = completed_at.hour
        hour_counts[h] = hour_counts.get(h, 0) + 1

    best_hours = sorted(hour_counts.items(), key=lambda x: -x[1])[:3]

    return Response({
        "completed_today": completed_today,
        "overdue": overdue,
        "by_list": by_list,
        "best_hours": [{"hour": h, "count": c} for h, c in best_hours],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def monthly_history(request):
    """Histogramme mensuel des tâches terminées sur 12 mois."""
    now = timezone.now()
    result = []
    for i in range(11, -1, -1):
        month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(seconds=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(seconds=1)
        count = Task.objects.filter(
            user=request.user,
            status=Task.Status.COMPLETED,
            completed_at__gte=month_start,
            completed_at__lte=month_end,
        ).count()
        result.append({"month": month_start.strftime("%Y-%m"), "count": count})
    return Response(result)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def productivity_score(request):
    """Score de productivité : complétions à l'heure vs en retard."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    completed_on_time = Task.objects.filter(
        user=request.user,
        status=Task.Status.COMPLETED,
        completed_at__gte=today_start,
        completed_at__lte=today_end,
        due_date__gte=today_start,
    ).count()

    completed_late = Task.objects.filter(
        user=request.user,
        status=Task.Status.COMPLETED,
        completed_at__gte=today_start,
        completed_at__lte=today_end,
        due_date__lt=today_start,
    ).count()

    still_overdue = Task.objects.filter(
        user=request.user,
        status=Task.Status.NORMAL,
        due_date__lt=today_start,
    ).count()

    score = max(0, completed_on_time * 10 - still_overdue * 5 + completed_late * 3)

    # Niveau basé sur les complétions totales
    total_completed = Task.objects.filter(
        user=request.user, status=Task.Status.COMPLETED
    ).count()
    level = min(50, 1 + total_completed // 20)

    return Response({
        "score": score,
        "level": level,
        "completed_on_time": completed_on_time,
        "completed_late": completed_late,
        "overdue": still_overdue,
    })
