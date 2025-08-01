# Generated by Django 4.2.23 on 2025-06-27 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0060_delete_report_delete_reportcategory'),
    ]

    operations = [
        migrations.CreateModel(
            name='Hubspot_Division',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('division_name', models.CharField(blank=True, max_length=255, null=True)),
                ('division_label', models.CharField(blank=True, max_length=255, null=True)),
                ('division_code', models.CharField(blank=True, max_length=100, null=True)),
                ('hs_object_id', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_createdate', models.DateTimeField(blank=True, null=True)),
                ('hs_lastmodifieddate', models.DateTimeField(blank=True, null=True)),
                ('hs_pipeline', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_pipeline_stage', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_all_accessible_team_ids', models.JSONField(blank=True, null=True)),
                ('hs_all_assigned_business_unit_ids', models.JSONField(blank=True, null=True)),
                ('hs_all_owner_ids', models.JSONField(blank=True, null=True)),
                ('hs_all_team_ids', models.JSONField(blank=True, null=True)),
                ('hs_created_by_user_id', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_merged_object_ids', models.JSONField(blank=True, null=True)),
                ('hs_object_source', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_object_source_detail_1', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_object_source_detail_2', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_object_source_detail_3', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_object_source_id', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_object_source_label', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_object_source_user_id', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_owning_teams', models.JSONField(blank=True, null=True)),
                ('hs_read_only', models.BooleanField(blank=True, null=True)),
                ('hs_shared_team_ids', models.JSONField(blank=True, null=True)),
                ('hs_shared_user_ids', models.JSONField(blank=True, null=True)),
                ('hs_unique_creation_key', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_updated_by_user_id', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_user_ids_of_all_notification_followers', models.JSONField(blank=True, null=True)),
                ('hs_user_ids_of_all_notification_unfollowers', models.JSONField(blank=True, null=True)),
                ('hs_user_ids_of_all_owners', models.JSONField(blank=True, null=True)),
                ('hs_was_imported', models.BooleanField(blank=True, null=True)),
                ('status', models.CharField(blank=True, max_length=100, null=True)),
                ('region', models.CharField(blank=True, max_length=100, null=True)),
                ('manager_name', models.CharField(blank=True, max_length=255, null=True)),
                ('manager_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('address1', models.CharField(blank=True, max_length=255, null=True)),
                ('address2', models.CharField(blank=True, max_length=255, null=True)),
                ('city', models.CharField(blank=True, max_length=100, null=True)),
                ('state', models.CharField(blank=True, max_length=10, null=True)),
                ('zip', models.CharField(blank=True, max_length=20, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('archived', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'HubSpot Division',
                'verbose_name_plural': 'HubSpot Divisions',
                'db_table': 'ingestion_hubspot_division',
            },
        ),
    ]
