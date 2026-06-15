import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Habit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("icon", models.CharField(blank=True, max_length=64)),
                ("color", models.CharField(blank=True, max_length=16)),
                ("frequency", models.CharField(choices=[("daily", "Daily"), ("weekly", "Weekly"), ("specific_days", "Specific Days"), ("interval", "Interval"), ("weekly_goal", "Weekly Goal")], default="daily", max_length=16)),
                ("freq_config", models.JSONField(blank=True, default=dict)),
                ("goal_type", models.CharField(choices=[("binary", "Binary"), ("numeric", "Numeric")], default="binary", max_length=16)),
                ("goal_value", models.FloatField(default=1.0)),
                ("goal_unit", models.CharField(blank=True, max_length=32)),
                ("motto", models.CharField(blank=True, max_length=255)),
                ("check_in_mode", models.CharField(choices=[("auto", "Auto"), ("manual", "Manual"), ("binary", "Binary")], default="binary", max_length=16)),
                ("auto_increment", models.FloatField(default=1.0)),
                ("sort_order", models.BigIntegerField(default=0)),
                ("archived", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="habits", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["sort_order"]},
        ),
        migrations.CreateModel(
            name="HabitReminder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("time", models.TimeField()),
                ("habit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reminders", to="habits.habit")),
            ],
            options={"ordering": ["time"]},
        ),
        migrations.CreateModel(
            name="HabitCheckIn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("quantity", models.FloatField(default=1.0)),
                ("note", models.TextField(blank=True)),
                ("completed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("habit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="checkins", to="habits.habit")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
