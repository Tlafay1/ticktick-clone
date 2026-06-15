import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0004_task_estimated_pomos"),
    ]

    operations = [
        migrations.CreateModel(
            name="FocusSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("mode", models.CharField(choices=[("pomodoro", "Pomodoro"), ("stopwatch", "Stopwatch")], default="pomodoro", max_length=16)),
                ("session_type", models.CharField(choices=[("work", "Work"), ("short_break", "Short Break"), ("long_break", "Long Break")], default="work", max_length=16)),
                ("start_at", models.DateTimeField()),
                ("end_at", models.DateTimeField(blank=True, null=True)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("task", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="focus_sessions", to="tasks.task")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="focus_sessions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-start_at"]},
        ),
    ]
