# Generated manually on 2025-08-07 18:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0115_delete_activeprospect_event_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeadConduit_Lead',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lead_id', models.CharField(db_index=True, max_length=100, unique=True)),
                ('event_id', models.CharField(db_index=True, max_length=100)),
                ('first_name', models.CharField(blank=True, max_length=200, null=True)),
                ('last_name', models.CharField(blank=True, max_length=200, null=True)),
                ('email', models.EmailField(blank=True, db_index=True, max_length=254, null=True)),
                ('phone', models.CharField(blank=True, db_index=True, max_length=50, null=True)),
                ('address', models.CharField(blank=True, max_length=500, null=True)),
                ('city', models.CharField(blank=True, max_length=200, null=True)),
                ('state', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('zip_code', models.CharField(blank=True, db_index=True, max_length=50, null=True)),
                ('country', models.CharField(blank=True, max_length=100, null=True)),
                ('flow_name', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('source_name', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('outcome', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('reason', models.TextField(blank=True, null=True)),
                ('submitted_utc', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('lead_data', models.JSONField(blank=True, default=dict)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'LeadConduit Lead',
                'verbose_name_plural': 'LeadConduit Leads',
                'db_table': 'ingestion_leadconduit_lead',
                'ordering': ['-submitted_utc'],
            },
        ),
        migrations.AddIndex(
            model_name='leadconduit_lead',
            index=models.Index(fields=['email', 'phone'], name='ingestion_l_email_ff7575_idx'),
        ),
        migrations.AddIndex(
            model_name='leadconduit_lead',
            index=models.Index(fields=['state', 'zip_code'], name='ingestion_l_state_3a6dc9_idx'),
        ),
        migrations.AddIndex(
            model_name='leadconduit_lead',
            index=models.Index(fields=['flow_name', 'source_name'], name='ingestion_l_flow_na_21f4b7_idx'),
        ),
        migrations.AddIndex(
            model_name='leadconduit_lead',
            index=models.Index(fields=['outcome', 'submitted_utc'], name='ingestion_l_outcome_1a6dc9_idx'),
        ),
        migrations.AddIndex(
            model_name='leadconduit_lead',
            index=models.Index(fields=['submitted_utc'], name='ingestion_l_submitt_2b7b89_idx'),
        ),
    ]
