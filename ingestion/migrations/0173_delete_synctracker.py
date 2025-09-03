# Generated manually to delete SyncTracker model as it's no longer used
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0172_rename_ingestionschedule_to_syncschedule'),
    ]

    operations = [
        migrations.DeleteModel(
            name='SyncTracker',
        ),
    ]
