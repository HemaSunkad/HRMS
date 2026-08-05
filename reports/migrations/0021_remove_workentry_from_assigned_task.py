from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0020_workentry_from_assigned_task'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='workentry',
            name='from_assigned_task',
        ),
    ]