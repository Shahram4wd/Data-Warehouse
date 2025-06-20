# Generated by Django 5.2.1 on 2025-06-02 09:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0008_appointmentoutcometype_alter_appointmentoutcome_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointment',
            name='add_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='duration',
            field=models.DurationField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='is_complete',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='spouses_present',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='appointmenttype',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='appointmenttype',
            name='label',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
