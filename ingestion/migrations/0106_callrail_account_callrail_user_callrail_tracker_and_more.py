# Generated by Django 4.2.23 on 2025-07-31 03:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0105_delete_salespro_appointment_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CallRail_Account',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('outbound_recording_enabled', models.BooleanField(default=False)),
                ('hipaa_account', models.BooleanField(default=False)),
                ('numeric_id', models.BigIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'CallRail Account',
                'verbose_name_plural': 'CallRail Accounts',
                'db_table': 'ingestion_callrail_account',
            },
        ),
        migrations.CreateModel(
            name='CallRail_User',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('role', models.CharField(blank=True, max_length=100, null=True)),
                ('permissions', models.JSONField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'CallRail User',
                'verbose_name_plural': 'CallRail Users',
                'db_table': 'ingestion_CallRail_user',
                'indexes': [models.Index(fields=['email'], name='ingestion_C_email_8d2e02_idx'), models.Index(fields=['role'], name='ingestion_C_role_89888b_idx'), models.Index(fields=['is_active'], name='ingestion_C_is_acti_1b30aa_idx')],
            },
        ),
        migrations.CreateModel(
            name='CallRail_Tracker',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('type', models.CharField(max_length=50)),
                ('status', models.CharField(max_length=50)),
                ('destination_number', models.CharField(max_length=20)),
                ('whisper_message', models.TextField(blank=True, null=True)),
                ('sms_enabled', models.BooleanField(default=False)),
                ('sms_supported', models.BooleanField(default=False)),
                ('disabled_at', models.DateTimeField(blank=True, null=True)),
                ('tracking_numbers', models.JSONField(default=list)),
                ('company', models.JSONField(blank=True, null=True)),
                ('call_flow', models.JSONField(blank=True, null=True)),
                ('source', models.JSONField(blank=True, null=True)),
                ('api_created_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'CallRail Tracker',
                'verbose_name_plural': 'CallRail Trackers',
                'db_table': 'ingestion_CallRail_tracker',
                'indexes': [models.Index(fields=['type'], name='ingestion_C_type_37310b_idx'), models.Index(fields=['status'], name='ingestion_C_status_279f95_idx'), models.Index(fields=['destination_number'], name='ingestion_C_destina_1d563a_idx')],
            },
        ),
        migrations.CreateModel(
            name='CallRail_TextMessage',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('company_id', models.CharField(blank=True, max_length=50, null=True)),
                ('direction', models.CharField(max_length=20)),
                ('tracking_phone_number', models.CharField(max_length=20)),
                ('customer_phone_number', models.CharField(max_length=20)),
                ('message', models.TextField()),
                ('sent_at', models.DateTimeField()),
                ('status', models.CharField(blank=True, max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'CallRail Text Message',
                'verbose_name_plural': 'CallRail Text Messages',
                'db_table': 'ingestion_CallRail_text_message',
                'indexes': [models.Index(fields=['sent_at'], name='ingestion_C_sent_at_802efc_idx'), models.Index(fields=['direction'], name='ingestion_C_directi_a1065e_idx'), models.Index(fields=['customer_phone_number'], name='ingestion_C_custome_3487af_idx'), models.Index(fields=['tracking_phone_number'], name='ingestion_C_trackin_7d7ea1_idx'), models.Index(fields=['company_id'], name='ingestion_C_company_29f895_idx')],
            },
        ),
        migrations.CreateModel(
            name='CallRail_Tag',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('color', models.CharField(blank=True, max_length=20, null=True)),
                ('company_id', models.CharField(blank=True, max_length=50, null=True)),
                ('configuration', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'CallRail Tag',
                'verbose_name_plural': 'CallRail Tags',
                'db_table': 'ingestion_CallRail_tag',
                'indexes': [models.Index(fields=['name'], name='ingestion_C_name_327106_idx'), models.Index(fields=['company_id'], name='ingestion_C_company_2acdb6_idx')],
            },
        ),
        migrations.CreateModel(
            name='CallRail_FormSubmission',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('company_id', models.CharField(max_length=50)),
                ('person_id', models.CharField(blank=True, max_length=50, null=True)),
                ('form_url', models.URLField()),
                ('landing_page_url', models.URLField(blank=True, null=True)),
                ('form_data', models.JSONField()),
                ('submission_time', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'CallRail Form Submission',
                'verbose_name_plural': 'CallRail Form Submissions',
                'db_table': 'ingestion_CallRail_form_submission',
                'indexes': [models.Index(fields=['submission_time'], name='ingestion_C_submiss_4b9c53_idx'), models.Index(fields=['company_id'], name='ingestion_C_company_3d8878_idx'), models.Index(fields=['person_id'], name='ingestion_C_person__6ac5c5_idx')],
            },
        ),
        migrations.CreateModel(
            name='CallRail_Company',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('status', models.CharField(max_length=50)),
                ('time_zone', models.CharField(max_length=100)),
                ('dni_active', models.BooleanField(blank=True, null=True)),
                ('script_url', models.TextField(blank=True, null=True)),
                ('callscribe_enabled', models.BooleanField(default=False)),
                ('lead_scoring_enabled', models.BooleanField(default=False)),
                ('swap_exclude_jquery', models.BooleanField(blank=True, null=True)),
                ('swap_ppc_override', models.BooleanField(blank=True, null=True)),
                ('swap_landing_override', models.CharField(blank=True, max_length=255, null=True)),
                ('swap_cookie_duration', models.IntegerField(default=6)),
                ('swap_cookie_duration_unit', models.CharField(default='months', max_length=20)),
                ('callscore_enabled', models.BooleanField(default=False)),
                ('keyword_spotting_enabled', models.BooleanField(default=False)),
                ('form_capture', models.BooleanField(default=False)),
                ('disabled_at', models.DateTimeField(blank=True, null=True)),
                ('api_created_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'CallRail Company',
                'verbose_name_plural': 'CallRail Companies',
                'db_table': 'ingestion_CallRail_company',
                'indexes': [models.Index(fields=['status'], name='ingestion_C_status_86e167_idx'), models.Index(fields=['time_zone'], name='ingestion_C_time_zo_17cc68_idx')],
            },
        ),
        migrations.CreateModel(
            name='CallRail_Call',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('answered', models.BooleanField(default=False)),
                ('business_phone_number', models.CharField(blank=True, max_length=20, null=True)),
                ('customer_city', models.CharField(blank=True, max_length=100, null=True)),
                ('customer_country', models.CharField(blank=True, max_length=100, null=True)),
                ('customer_name', models.CharField(blank=True, max_length=255, null=True)),
                ('customer_phone_number', models.CharField(max_length=20)),
                ('customer_state', models.CharField(blank=True, max_length=50, null=True)),
                ('direction', models.CharField(max_length=20)),
                ('duration', models.IntegerField(default=0)),
                ('recording', models.URLField(blank=True, null=True)),
                ('recording_duration', models.CharField(blank=True, max_length=20, null=True)),
                ('recording_player', models.URLField(blank=True, null=True)),
                ('start_time', models.DateTimeField()),
                ('tracking_phone_number', models.CharField(max_length=20)),
                ('voicemail', models.BooleanField(default=False)),
                ('agent_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('call_type', models.CharField(blank=True, max_length=50, null=True)),
                ('campaign', models.CharField(blank=True, max_length=255, null=True)),
                ('company_id', models.CharField(blank=True, max_length=50, null=True)),
                ('company_name', models.CharField(blank=True, max_length=255, null=True)),
                ('note', models.TextField(blank=True, null=True)),
                ('lead_status', models.CharField(blank=True, max_length=100, null=True)),
                ('value', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('tags', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'CallRail Call',
                'verbose_name_plural': 'CallRail Calls',
                'db_table': 'ingestion_CallRail_call',
                'indexes': [models.Index(fields=['start_time'], name='ingestion_C_start_t_830648_idx'), models.Index(fields=['customer_phone_number'], name='ingestion_C_custome_d1f10f_idx'), models.Index(fields=['tracking_phone_number'], name='ingestion_C_trackin_6f6754_idx'), models.Index(fields=['answered'], name='ingestion_C_answere_fc755c_idx'), models.Index(fields=['direction'], name='ingestion_C_directi_8d4033_idx'), models.Index(fields=['company_id'], name='ingestion_C_company_52e3d6_idx'), models.Index(fields=['lead_status'], name='ingestion_C_lead_st_750391_idx')],
            },
        ),
    ]
