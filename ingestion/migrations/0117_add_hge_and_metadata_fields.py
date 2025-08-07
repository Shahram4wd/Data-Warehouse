# Generated manually on 2025-08-07 to add HGE and metadata fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0116_recreate_leadconduit_lead'),
    ]

    operations = [
        # Add HGE-specific fields
        migrations.AddField(
            model_name='leadconduit_lead',
            name='note_hge',
            field=models.TextField(blank=True, help_text='HGE lead notes', null=True),
        ),
        migrations.AddField(
            model_name='leadconduit_lead',
            name='owner_hge',
            field=models.CharField(blank=True, help_text='HGE lead owner name', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='leadconduit_lead',
            name='owneremail_hge',
            field=models.EmailField(blank=True, help_text='HGE lead owner email', max_length=254, null=True),
        ),
        migrations.AddField(
            model_name='leadconduit_lead',
            name='ownerid_hge',
            field=models.CharField(blank=True, db_index=True, help_text='HGE lead owner ID', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='leadconduit_lead',
            name='salesrabbit_lead_id_hge',
            field=models.CharField(blank=True, db_index=True, help_text='SalesRabbit lead ID', max_length=50, null=True),
        ),
        # Add metadata storage fields
        migrations.AddField(
            model_name='leadconduit_lead',
            name='phone_metadata',
            field=models.JSONField(blank=True, default=dict, help_text='Phone validation metadata from API'),
        ),
        migrations.AddField(
            model_name='leadconduit_lead',
            name='email_metadata',
            field=models.JSONField(blank=True, default=dict, help_text='Email validation metadata from API'),
        ),
        migrations.AddField(
            model_name='leadconduit_lead',
            name='address_metadata',
            field=models.JSONField(blank=True, default=dict, help_text='Address validation metadata from API'),
        ),
        # Add new indexes for HGE fields
        migrations.AddIndex(
            model_name='leadconduit_lead',
            index=models.Index(fields=['ownerid_hge'], name='ingestion_l_ownerid_hge_idx'),
        ),
        migrations.AddIndex(
            model_name='leadconduit_lead',
            index=models.Index(fields=['salesrabbit_lead_id_hge'], name='ingestion_l_salesrabbit_hge_idx'),
        ),
        migrations.AddIndex(
            model_name='leadconduit_lead',
            index=models.Index(fields=['owner_hge', 'submitted_utc'], name='ingestion_l_owner_submitted_idx'),
        ),
    ]
