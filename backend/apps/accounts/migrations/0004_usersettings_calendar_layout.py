from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_usersettings_hidden_hours_end_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='calendar_layout',
            field=models.CharField(default='classic', max_length=16),
        ),
    ]
