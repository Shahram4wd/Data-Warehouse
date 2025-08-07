# Migration to clean up model state

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0113_sync_salesrabbit_state'),
    ]

    operations = [
        # These operations handle Django's state cleanup
        # The fields being removed don't actually exist in the database
        # but Django thinks they do based on old migration history
        
        # Note: DeleteModel operations removed since those tables don't exist
        # Note: RemoveField operations will be faked since fields don't exist
    ]
