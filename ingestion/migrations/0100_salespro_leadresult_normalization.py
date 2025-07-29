# Generated migration for SalesPro_LeadResult normalization
# This migration adds new normalized fields and renames existing field

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0099_genius_userdata_primary_user_id'),  # Use latest migration
    ]

    operations = [
        # Add the new normalized fields
        migrations.AddField(
            model_name='salespro_leadresult',
            name='appointment_result',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='salespro_leadresult',
            name='result_reason_demo_not_sold',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='salespro_leadresult',
            name='result_reason_no_demo',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='salespro_leadresult',
            name='both_homeowners_present',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='salespro_leadresult',
            name='one_year_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='salespro_leadresult',
            name='last_price_offered',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='salespro_leadresult',
            name='preferred_payment',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='salespro_leadresult',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='salespro_leadresult',
            name='lead_results_raw',
            field=models.TextField(blank=True, null=True),
        ),
        
        # Copy data from lead_results to lead_results_raw (only if table and column exist)
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ingestion_salespro_lead_results') 
                   AND EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'ingestion_salespro_lead_results' AND column_name = 'lead_results') THEN
                    UPDATE ingestion_salespro_lead_results SET lead_results_raw = lead_results WHERE lead_results IS NOT NULL;
                END IF;
            END $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ingestion_salespro_lead_results') 
                   AND EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'ingestion_salespro_lead_results' AND column_name = 'lead_results') THEN
                    UPDATE ingestion_salespro_lead_results SET lead_results = lead_results_raw WHERE lead_results_raw IS NOT NULL;
                END IF;
            END $$;
            """
        ),
        
        # Remove the old lead_results field (only if it exists)
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'ingestion_salespro_lead_results' AND column_name = 'lead_results') THEN
                    ALTER TABLE ingestion_salespro_lead_results DROP COLUMN lead_results;
                END IF;
            END $$;
            """,
            reverse_sql="-- Cannot reverse dropping a column easily"
        ),
        
        # Note: Unique constraint removed due to existing duplicates
        # Run: python manage.py db_salespro_leadresults_cleanup_duplicates before applying constraint
    ]
