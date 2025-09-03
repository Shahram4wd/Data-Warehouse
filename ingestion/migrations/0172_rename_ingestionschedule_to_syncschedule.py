# Generated manually to rename IngestionSchedule to SyncSchedule and move table to orchestration schema
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0171_ingestionschedule_ingestionrun_and_more'),
    ]

    operations = [
        # Rename the model first so Django state matches code
        migrations.RenameModel(
            old_name='IngestionSchedule',
            new_name='SyncSchedule',
        ),
        # Move/rename the underlying table into the orchestration schema
        migrations.AlterModelTable(
            name='syncschedule',
            table='orchestration.sync_schedule',
        ),
        # Drop the unused IngestionRun table since we use SyncHistory instead
        migrations.DeleteModel(
            name='IngestionRun',
        ),
    ]
