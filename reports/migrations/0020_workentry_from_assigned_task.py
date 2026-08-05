from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0019_workentry_accumulated_minutes_workentry_pause_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='workentry',
            name='from_assigned_task',
            field=models.BooleanField(default=False),
        ),
    ]