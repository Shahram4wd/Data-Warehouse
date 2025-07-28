# Generated migration for changing LeadResult to use estimate_id as primary key
# This will delete existing data and recreate the table

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0100_salespro_leadresult_normalization'),
    ]

    operations = [
        # Drop the existing table completely and recreate with new structure
        migrations.RunSQL(
            "DROP TABLE IF EXISTS ingestion_salespro_leadresult CASCADE;",
            reverse_sql="-- Cannot reverse table drop"
        ),
        
        # Recreate the table with estimate_id as primary key
        migrations.CreateModel(
            name='SalesPro_LeadResult',
            fields=[
                ('estimate_id', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('company_id', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
                ('appointment_result', models.CharField(blank=True, max_length=255, null=True)),
                ('result_reason_demo_not_sold', models.CharField(blank=True, max_length=255, null=True)),
                ('result_reason_no_demo', models.CharField(blank=True, max_length=255, null=True)),
                ('both_homeowners_present', models.CharField(blank=True, max_length=10, null=True)),
                ('one_year_price', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('last_price_offered', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('preferred_payment', models.CharField(blank=True, max_length=255, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('lead_results_raw', models.TextField(blank=True, help_text='Original JSON data for reference', null=True)),
            ],
            options={
                'verbose_name': 'Lead Result',
                'verbose_name_plural': 'Lead Results',
                'db_table': 'ingestion_salespro_leadresult',
                'ordering': ['-updated_at'],
            },
        ),
    ]
