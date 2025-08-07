# Migration to sync Django state with actual database schema

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0112_salesrabbit_fields_update'),
    ]

    operations = [
        # Use state operations to tell Django about the current actual state
        # without making database changes since the schema is already correct
        
        migrations.AlterField(
            model_name='salesrabbit_lead',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='salesrabbit_lead',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='salesrabbit_lead',
            name='appointment',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='salesrabbit_lead',
            name='files',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
