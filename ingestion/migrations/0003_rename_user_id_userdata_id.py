# Generated by Django 5.2.1 on 2025-05-27 17:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0002_remove_userdata_lead_call_center_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userdata',
            old_name='user_id',
            new_name='id',
        ),
    ]
