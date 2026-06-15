from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0003_add_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="estimated_pomos",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
