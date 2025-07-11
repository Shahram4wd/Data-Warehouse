# Generated by Django 5.2.1 on 2025-06-05 16:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0021_salespro_users_alter_marketingsource_table'),
    ]

    operations = [
        migrations.CreateModel(
            name='Genius_UserTitle',
            fields=[
                ('id', models.SmallIntegerField(primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, max_length=100, null=True)),
                ('abbreviation', models.CharField(blank=True, max_length=10, null=True)),
                ('roles', models.CharField(blank=True, max_length=256, null=True)),
                ('type_id', models.SmallIntegerField(blank=True, null=True)),
                ('section_id', models.SmallIntegerField(blank=True, null=True)),
                ('sort', models.SmallIntegerField(blank=True, null=True)),
                ('pay_component_group_id', models.SmallIntegerField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_unique_per_division', models.BooleanField(default=False)),
            ],
        ),
        migrations.AlterField(
            model_name='genius_userdata',
            name='add_datetime',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='genius_userdata',
            name='time_zone_name',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
