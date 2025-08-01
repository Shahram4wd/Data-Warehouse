# Generated by Django 4.2.23 on 2025-07-18 17:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0096_alter_hubspot_contact_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlertRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Rule name', max_length=255, unique=True)),
                ('alert_type', models.CharField(help_text='Type of alert this rule generates', max_length=50)),
                ('severity', models.CharField(help_text='Severity level for alerts from this rule', max_length=20)),
                ('message_template', models.TextField(help_text='Template for alert messages')),
                ('condition_config', models.JSONField(default=dict, help_text='Condition configuration')),
                ('cooldown_minutes', models.IntegerField(default=60, help_text='Cooldown period in minutes')),
                ('max_alerts_per_hour', models.IntegerField(default=5, help_text='Maximum alerts per hour')),
                ('enabled', models.BooleanField(default=True, help_text='Whether the rule is enabled')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
                'indexes': [models.Index(fields=['alert_type'], name='ingestion_a_alert_t_48ab2f_idx'), models.Index(fields=['enabled'], name='ingestion_a_enabled_500f2d_idx')],
            },
        ),
        migrations.CreateModel(
            name='AlertModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alert_id', models.CharField(help_text='Unique identifier for the alert', max_length=255, unique=True)),
                ('alert_type', models.CharField(help_text='Type of alert (performance, error_rate, etc.)', max_length=50)),
                ('severity', models.CharField(help_text='Alert severity level', max_length=20)),
                ('title', models.CharField(help_text='Alert title', max_length=255)),
                ('message', models.TextField(help_text='Alert message')),
                ('details', models.JSONField(default=dict, help_text='Additional alert details')),
                ('timestamp', models.DateTimeField(help_text='When the alert was created')),
                ('source', models.CharField(default='monitoring', help_text='Source of the alert', max_length=100)),
                ('resolved', models.BooleanField(default=False, help_text='Whether the alert has been resolved')),
                ('resolution_time', models.DateTimeField(blank=True, help_text='When the alert was resolved', null=True)),
                ('resolution_notes', models.TextField(blank=True, help_text='Notes about the resolution', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'ingestion_alerts',
                'ordering': ['-timestamp'],
                'indexes': [models.Index(fields=['alert_type'], name='ingestion_a_alert_t_390b27_idx'), models.Index(fields=['severity'], name='ingestion_a_severit_8f7415_idx'), models.Index(fields=['resolved'], name='ingestion_a_resolve_0265d9_idx'), models.Index(fields=['timestamp'], name='ingestion_a_timesta_4ddc7c_idx'), models.Index(fields=['source'], name='ingestion_a_source_03722e_idx')],
            },
        ),
    ]
