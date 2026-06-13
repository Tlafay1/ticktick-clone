# Generated migration
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='filter_rules',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='project',
            name='grouping',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='project',
            name='hidden_from_smart_lists',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='project',
            name='is_smart',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='project',
            name='sorting',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
