# Generated by Django 5.2.1 on 2025-05-28 16:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0004_synctracker_remove_userdata_user_associations_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='synctracker',
            name='last_synced_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='synctracker',
            name='object_name',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
