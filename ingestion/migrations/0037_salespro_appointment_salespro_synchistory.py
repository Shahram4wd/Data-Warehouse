# Generated by Django 4.2.23 on 2025-06-19 05:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0036_remove_arrivy_division'),
    ]

    operations = [
        migrations.CreateModel(
            name='SalesPro_Appointment',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('is_sale', models.BooleanField(default=False)),
                ('result_full_string', models.TextField(blank=True, null=True)),
                ('customer_last_name', models.CharField(blank=True, max_length=100, null=True)),
                ('customer_first_name', models.CharField(blank=True, max_length=100, null=True)),
                ('customer_estimate_name', models.CharField(blank=True, max_length=255, null=True)),
                ('salesrep_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('salesrep_first_name', models.CharField(blank=True, max_length=100, null=True)),
                ('salesrep_last_name', models.CharField(blank=True, max_length=100, null=True)),
                ('sale_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('imported_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'SalesPro Appointment',
                'verbose_name_plural': 'SalesPro Appointments',
                'db_table': 'salespro_appointment',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SalesPro_SyncHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_type', models.CharField(max_length=50)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('records_processed', models.IntegerField(default=0)),
                ('records_created', models.IntegerField(default=0)),
                ('records_updated', models.IntegerField(default=0)),
                ('status', models.CharField(default='in_progress', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('file_path', models.CharField(blank=True, max_length=500, null=True)),
            ],
            options={
                'verbose_name': 'SalesPro Sync History',
                'verbose_name_plural': 'SalesPro Sync Histories',
                'db_table': 'salespro_sync_history',
                'ordering': ['-started_at'],
            },
        ),
    ]
