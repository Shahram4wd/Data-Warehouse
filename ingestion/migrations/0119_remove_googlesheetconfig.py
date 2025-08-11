# Generated manually to remove GoogleSheetConfig model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0118_googlesheetconfig_googlesheetmarketinglead_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='GoogleSheetConfig',
        ),
    ]
