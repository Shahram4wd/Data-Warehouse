# Generated manually for multi-year Google Sheets marketing leads support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0191_salespro_estimate_created_at_and_more'),
    ]

    operations = [
        # Drop and recreate the table completely since it's empty
        migrations.RunSQL(
            "DROP TABLE IF EXISTS gsheet_marketing_lead CASCADE;",
            reverse_sql="-- Cannot reverse table drop"
        ),
        
        # Recreate the table with the new structure
        migrations.CreateModel(
            name='GoogleSheetMarketingLead',
            fields=[
                ('id', models.CharField(help_text='Format: YYYY-row_number', max_length=20, primary_key=True, serialize=False)),
                ('year', models.PositiveIntegerField(help_text='Year from sheet source (2024, 2025, etc.)')),
                ('sheet_row_number', models.PositiveIntegerField(help_text='Original row number from sheet')),
                ('sync_created_at', models.DateTimeField(auto_now_add=True, help_text='When this record was first synced')),
                ('sync_updated_at', models.DateTimeField(auto_now=True, help_text='When this record was last updated via sync')),
                ('sheet_last_modified', models.DateTimeField(blank=True, help_text='Last modified timestamp from sheet', null=True)),
                ('created_at', models.DateTimeField(blank=True, help_text='Lead creation timestamp from source', null=True)),
                ('first_name', models.CharField(blank=True, max_length=100, null=True)),
                ('last_name', models.CharField(blank=True, max_length=100, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=20, null=True)),
                ('email_address', models.EmailField(blank=True, max_length=254, null=True)),
                ('utm_campaign', models.CharField(blank=True, max_length=200, null=True)),
                ('utm_term', models.CharField(blank=True, max_length=200, null=True)),
                ('utm_content', models.CharField(blank=True, max_length=200, null=True)),
                ('page_source_name', models.CharField(blank=True, max_length=200, null=True)),
                ('page_url', models.URLField(blank=True, max_length=500, null=True)),
                ('variant', models.CharField(blank=True, max_length=100, null=True)),
                ('click_id', models.CharField(blank=True, max_length=100, null=True)),
                ('click_type', models.CharField(blank=True, max_length=50, null=True)),
                ('division', models.CharField(blank=True, max_length=100, null=True)),
                ('form_submit_zipcode', models.CharField(blank=True, max_length=10, null=True)),
                ('marketing_zip_check', models.CharField(blank=True, max_length=200, null=True)),
                ('lead_type', models.CharField(blank=True, max_length=100, null=True)),
                ('connection_status', models.CharField(blank=True, max_length=100, null=True)),
                ('contact_reason', models.CharField(blank=True, max_length=200, null=True)),
                ('lead_set', models.BooleanField(blank=True, null=True)),
                ('no_set_reason', models.CharField(blank=True, max_length=200, null=True)),
                ('recording_duration', models.PositiveIntegerField(blank=True, null=True)),
                ('hold_time', models.PositiveIntegerField(blank=True, null=True)),
                ('first_call_date_time', models.DateTimeField(blank=True, null=True)),
                ('call_attempts', models.PositiveIntegerField(blank=True, null=True)),
                ('after_hours', models.CharField(blank=True, max_length=50, null=True)),
                ('call_notes', models.TextField(blank=True, null=True)),
                ('call_recording', models.URLField(blank=True, max_length=500, null=True)),
                ('manager_followup', models.BooleanField(blank=True, null=True)),
                ('callback_review', models.CharField(blank=True, max_length=200, null=True)),
                ('call_center', models.CharField(blank=True, max_length=100, null=True)),
                ('multiple_inquiry', models.BooleanField(blank=True, null=True)),
                ('preferred_appt_date', models.DateField(blank=True, null=True)),
                ('appt_set_by', models.CharField(blank=True, max_length=100, null=True)),
                ('set_appt_date', models.DateField(blank=True, null=True)),
                ('appt_date_time', models.DateTimeField(blank=True, null=True)),
                ('appt_result', models.CharField(blank=True, max_length=100, null=True)),
                ('appt_result_reason', models.CharField(blank=True, max_length=200, null=True)),
                ('appt_attempts', models.PositiveIntegerField(blank=True, null=True)),
                ('appointment_outcome', models.CharField(blank=True, max_length=100, null=True)),
                ('appointment_outcome_type', models.CharField(blank=True, max_length=100, null=True)),
                ('spouses_present', models.BooleanField(blank=True, null=True)),
                ('keyword', models.CharField(blank=True, max_length=200, null=True)),
                ('adgroup_name', models.CharField(blank=True, max_length=200, null=True)),
                ('adgroup_id', models.CharField(blank=True, max_length=50, null=True)),
                ('csr_disposition', models.CharField(blank=True, max_length=100, null=True)),
                ('f9_list_name', models.CharField(blank=True, max_length=200, null=True)),
                ('f9_last_campaign', models.CharField(blank=True, max_length=200, null=True)),
                ('f9_sys_created_date', models.DateTimeField(blank=True, null=True)),
                ('marketsharp_address', models.CharField(blank=True, max_length=300, null=True)),
                ('total_job_value', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('cancel_job_value', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('genius_division', models.CharField(blank=True, max_length=100, null=True)),
                ('genius_marketing_source', models.CharField(blank=True, max_length=200, null=True)),
                ('marketsharp_source', models.CharField(blank=True, max_length=200, null=True)),
                ('event_show_type', models.CharField(blank=True, max_length=100, null=True)),
                ('event_show_name', models.CharField(blank=True, max_length=200, null=True)),
                ('google_ads_campaign_rename', models.CharField(blank=True, max_length=200, null=True)),
                ('channel', models.CharField(blank=True, max_length=100, null=True)),
                ('raw_data', models.JSONField(blank=True, help_text='Raw data from source', null=True)),
            ],
            options={
                'db_table': 'gsheet_marketing_lead',
                'indexes': [
                    models.Index(fields=['year', 'sheet_row_number'], name='gsheet_mark_year_row_idx'),
                    models.Index(fields=['year', 'created_at'], name='gsheet_mark_year_created_idx'),
                    models.Index(fields=['sync_created_at'], name='gsheet_mark_sync_created_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=['year', 'sheet_row_number'], name='unique_year_row_constraint'),
                ],
            },
        ),
    ]