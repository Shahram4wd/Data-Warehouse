# Generated by Django 4.2.23 on 2025-07-18 03:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0093_alter_hubspot_appointment_salespro_last_price_offered_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='hubspot_contact',
            options={'verbose_name': 'HubSpot Contact', 'verbose_name_plural': 'HubSpot Contacts'},
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='add_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='add_user_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='address1',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='address2',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='appointment_confirmed',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='appointment_end',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='appointment_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='appointment_name',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='appointment_response',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='appointment_services',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='appointment_start',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='appointment_status',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_appt_date',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_confirm_date',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_confirm_user',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_created_by',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_details',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_object_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_result_full_string',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_salesrep_first_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_salesrep_last_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_status',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_status_title',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_user',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_user_divison_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_user_external_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='arrivy_username',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='assign_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='cancel_reason',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='canvasser',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='canvasser_email',
            field=models.EmailField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='canvasser_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='complete_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='complete_outcome_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='complete_outcome_id_text',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='complete_user_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='confirm_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='confirm_user_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='confirm_with',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='created_by_make',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='created_by_user_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='div_cancel_reasons',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='division_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='duration',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='duration_number',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='error_details',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='f9_tfuid',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='first_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='genius_appointment_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='genius_quote_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='genius_quote_response',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='genius_quote_response_status',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='genius_response',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='genius_response_status',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='genius_resubmit',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='hscontact_id',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='is_complete',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='last_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='lead_services',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='leap_estimate_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='log',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='marketing_task_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='marketsharp_appt_type',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='merged_record_ids',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='object_create_datetime',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='object_last_modified_datetime',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='owner',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='owner_assigned_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='owners_main_team',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='phone1',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='phone2',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='pipeline',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='pipeline_stage',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='primary_source',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='product_interest_primary',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='product_interest_secondary',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='prospect_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='prospect_source_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='qc_cancel_reasons',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='record_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='record_source',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='record_source_detail_1',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='record_source_detail_2',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='record_source_detail_3',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_both_homeowners',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_consider_solar',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_customer_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_deadline',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_deposit_type',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_estimate_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_fileurl_contract',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_fileurl_estimate',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_financing',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_job_size',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_job_type',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_last_price_offered',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_one_year_price',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_preferred_payment',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_requested_start',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_result',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_result_notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_result_reason_demo',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='salespro_result_reason_no_demo',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='secondary_source',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='set_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='sourcefield',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='spouses_present',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='tester_test_delete',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='time',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='title',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='type_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='type_id_text',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='updated_by_user_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='user_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='hubspot_contact',
            name='year_built',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='hubspot_contact',
            name='city',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='hubspot_contact',
            name='email',
            field=models.EmailField(blank=True, max_length=255, null=True),
        ),
        migrations.AddIndex(
            model_name='hubspot_contact',
            index=models.Index(fields=['hscontact_id'], name='hubspot_con_hsconta_302e31_idx'),
        ),
        migrations.AddIndex(
            model_name='hubspot_contact',
            index=models.Index(fields=['appointment_id'], name='hubspot_con_appoint_b3c9f2_idx'),
        ),
        migrations.AddIndex(
            model_name='hubspot_contact',
            index=models.Index(fields=['email'], name='hubspot_con_email_968354_idx'),
        ),
        migrations.AddIndex(
            model_name='hubspot_contact',
            index=models.Index(fields=['phone1'], name='hubspot_con_phone1_f4ed7f_idx'),
        ),
        migrations.AddIndex(
            model_name='hubspot_contact',
            index=models.Index(fields=['appointment_start'], name='hubspot_con_appoint_3dd444_idx'),
        ),
        migrations.AddIndex(
            model_name='hubspot_contact',
            index=models.Index(fields=['appointment_status'], name='hubspot_con_appoint_9278b5_idx'),
        ),
        migrations.AddIndex(
            model_name='hubspot_contact',
            index=models.Index(fields=['first_name', 'last_name'], name='hubspot_con_first_n_4cf7c4_idx'),
        ),
        migrations.AddIndex(
            model_name='hubspot_contact',
            index=models.Index(fields=['city', 'state'], name='hubspot_con_city_bb55c8_idx'),
        ),
        migrations.AddIndex(
            model_name='hubspot_contact',
            index=models.Index(fields=['object_last_modified_datetime'], name='hubspot_con_object__a1ffc5_idx'),
        ),
        migrations.AddIndex(
            model_name='hubspot_contact',
            index=models.Index(fields=['created_at'], name='hubspot_con_created_3614ff_idx'),
        ),
        migrations.AddIndex(
            model_name='hubspot_contact',
            index=models.Index(fields=['updated_at'], name='hubspot_con_updated_11ed68_idx'),
        ),
        migrations.AlterModelTable(
            name='hubspot_contact',
            table='hubspot_contacts',
        ),
    ]
