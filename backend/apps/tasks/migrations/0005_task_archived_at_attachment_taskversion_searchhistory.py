import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0004_task_estimated_pomos"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="archived_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="Attachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="attachments/")),
                ("filename", models.CharField(max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=128)),
                ("size", models.PositiveIntegerField(default=0)),
                ("attachment_type", models.CharField(
                    choices=[("file", "File"), ("image", "Image"), ("audio", "Audio")],
                    default="file", max_length=16,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("task", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="attachments", to="tasks.task",
                )),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="TaskVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("task", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="versions", to="tasks.task",
                )),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="SearchHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("query", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="search_history", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
