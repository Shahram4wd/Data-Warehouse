# Generated by Django 4.2.23 on 2025-07-01 07:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0063_hubspot_zipcode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hubspot_appointment',
            name='salespro_financing',
            field=models.TextField(blank=True, null=True),
        ),
    ]
