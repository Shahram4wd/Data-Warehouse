# Generated by Django 4.2.23 on 2025-07-15 18:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0089_remove_hubspot_geniususer_created_by_user_id_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='hubspot_geniususer',
            name='createdAt',
        ),
        migrations.RemoveField(
            model_name='hubspot_geniususer',
            name='updatedAt',
        ),
    ]
