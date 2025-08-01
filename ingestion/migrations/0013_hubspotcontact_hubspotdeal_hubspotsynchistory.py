# Generated by Django 5.2.1 on 2025-06-02 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0012_division_is_inactive'),
    ]

    operations = [
        migrations.CreateModel(
            name='HubspotContact',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('address', models.TextField(blank=True, null=True)),
                ('campaign_name', models.CharField(blank=True, max_length=255, null=True)),
                ('city', models.CharField(blank=True, max_length=255, null=True)),
                ('createdate', models.DateTimeField(blank=True, null=True)),
                ('division', models.CharField(blank=True, max_length=255, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('firstname', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_google_click_id', models.CharField(blank=True, max_length=255, null=True)),
                ('hs_object_id', models.CharField(blank=True, max_length=255, null=True)),
                ('lastmodifieddate', models.DateTimeField(blank=True, null=True)),
                ('lastname', models.CharField(blank=True, max_length=255, null=True)),
                ('marketsharp_id', models.CharField(blank=True, max_length=255, null=True)),
                ('original_lead_source', models.CharField(blank=True, max_length=255, null=True)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('state', models.CharField(blank=True, max_length=255, null=True)),
                ('zip', models.CharField(blank=True, max_length=20, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('archived', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='HubspotDeal',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('deal_name', models.CharField(blank=True, max_length=255, null=True)),
                ('amount', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('closedate', models.DateTimeField(blank=True, null=True)),
                ('createdate', models.DateTimeField(blank=True, null=True)),
                ('dealstage', models.CharField(blank=True, max_length=255, null=True)),
                ('dealtype', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('hs_object_id', models.CharField(blank=True, max_length=255, null=True)),
                ('hubspot_owner_id', models.CharField(blank=True, max_length=255, null=True)),
                ('pipeline', models.CharField(blank=True, max_length=255, null=True)),
                ('division', models.CharField(blank=True, max_length=255, null=True)),
                ('priority', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='HubspotSyncHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('endpoint', models.CharField(max_length=100)),
                ('last_synced_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name_plural': 'Hubspot Sync Histories',
            },
        ),
    ]
