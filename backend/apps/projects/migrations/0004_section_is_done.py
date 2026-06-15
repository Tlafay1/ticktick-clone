from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0003_add_project_background"),
    ]

    operations = [
        migrations.AddField(
            model_name="section",
            name="is_done",
            field=models.BooleanField(default=False),
        ),
    ]
