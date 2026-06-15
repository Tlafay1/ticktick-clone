from django.urls import path

from .views import heatmap, monthly_history, productivity_score, summary

urlpatterns = [
    path("stats/heatmap/", heatmap, name="stats-heatmap"),
    path("stats/summary/", summary, name="stats-summary"),
    path("stats/monthly/", monthly_history, name="stats-monthly"),
    path("stats/productivity-score/", productivity_score, name="stats-score"),
]
