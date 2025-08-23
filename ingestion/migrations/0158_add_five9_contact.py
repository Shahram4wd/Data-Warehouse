# Generated migration for Five9Contact model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0157_create_orchestration_sync_history'),  # Latest migration
    ]

    operations = [
        migrations.CreateModel(
            name='Five9Contact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                
                # Standard Contact Fields
                ('number1', models.CharField(blank=True, max_length=20, null=True)),
                ('number2', models.CharField(blank=True, max_length=20, null=True)),
                ('number3', models.CharField(blank=True, max_length=20, null=True)),
                ('first_name', models.CharField(blank=True, max_length=100, null=True)),
                ('last_name', models.CharField(blank=True, max_length=100, null=True)),
                ('company', models.CharField(blank=True, max_length=255, null=True)),
                ('street', models.TextField(blank=True, null=True)),
                ('city', models.CharField(blank=True, max_length=100, null=True)),
                ('state', models.CharField(blank=True, max_length=50, null=True)),
                ('zip', models.CharField(blank=True, max_length=20, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                
                # System Fields
                ('contactID', models.CharField(blank=True, max_length=100, null=True)),
                ('sys_created_date', models.DateTimeField(blank=True, null=True)),
                ('sys_last_agent', models.CharField(blank=True, max_length=255, null=True)),
                ('sys_last_disposition', models.CharField(blank=True, max_length=255, null=True)),
                ('sys_last_disposition_time', models.DateTimeField(blank=True, null=True)),
                ('last_campaign', models.CharField(blank=True, max_length=255, null=True)),
                ('attempts', models.CharField(blank=True, max_length=50, null=True)),
                ('last_list', models.CharField(blank=True, max_length=255, null=True)),
                
                # Custom UUID Fields
                ('f65d759a_2250_4b2d_89a9_60796f624f72', models.CharField(blank=True, max_length=20, null=True)),
                ('field_4f347541_7c4d_4812_9190_e8dea6c0eb49', models.DateTimeField(blank=True, null=True)),
                ('field_80cf8462_cc10_41b8_a68a_5898cdba1e11', models.CharField(blank=True, max_length=255, null=True)),
                
                # Additional Custom Fields
                ('New_Contact_Field', models.DateTimeField(blank=True, null=True)),
                ('lead_source', models.CharField(blank=True, max_length=255, null=True)),
                ('DialAttempts', models.DecimalField(blank=True, decimal_places=0, max_digits=5, null=True)),
                ('XCounter', models.CharField(blank=True, max_length=255, null=True)),
                ('F9_list', models.CharField(blank=True, max_length=255, null=True)),
                ('DoNotDial', models.BooleanField(blank=True, null=True)),
                ('ggg', models.CharField(blank=True, max_length=255, null=True)),
                ('lead_prioritization', models.DecimalField(blank=True, decimal_places=0, max_digits=2, null=True)),
                ('metal_count', models.DecimalField(blank=True, decimal_places=0, max_digits=5, null=True)),
                
                # Agent Disposition Fields
                ('Last_Agent_Disposition', models.CharField(blank=True, max_length=255, null=True)),
                ('Last_Agent_Disposition_Date_Time', models.DateTimeField(blank=True, null=True)),
                
                # Business Fields
                ('Market', models.CharField(blank=True, max_length=255, null=True)),
                ('Secondary_Lead_Source', models.CharField(blank=True, max_length=255, null=True)),
                ('HubSpot_ContactID', models.CharField(blank=True, max_length=255, null=True)),
                ('Result', models.CharField(blank=True, max_length=255, null=True)),
                ('Product', models.CharField(blank=True, max_length=255, null=True)),
                ('Appointment_Date_and_Time', models.DateTimeField(blank=True, null=True)),
                ('Carrier', models.CharField(blank=True, max_length=255, null=True)),
                ('TFUID', models.CharField(blank=True, max_length=255, null=True)),
                ('Lead_Status', models.CharField(blank=True, max_length=255, null=True)),
                ('PC_Work_Finished', models.DateField(blank=True, null=True)),
                ('Total_Job_Amount', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('Position', models.CharField(blank=True, max_length=255, null=True)),
                ('Appointment_Date', models.DateField(blank=True, null=True)),
                
                # List Tracking
                ('list_name', models.CharField(max_length=255)),
                
                # Internal Sync Fields
                ('sync_created_at', models.DateTimeField(auto_now_add=True)),
                ('sync_updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'five9_contacts',
            },
        ),
        migrations.AddIndex(
            model_name='five9contact',
            index=models.Index(fields=['contactID'], name='five9_contacts_contact_id_idx'),
        ),
        migrations.AddIndex(
            model_name='five9contact',
            index=models.Index(fields=['list_name'], name='five9_contacts_list_name_idx'),
        ),
        migrations.AddIndex(
            model_name='five9contact',
            index=models.Index(fields=['sys_last_disposition_time'], name='five9_contacts_sys_last_disposition_time_idx'),
        ),
        migrations.AddIndex(
            model_name='five9contact',
            index=models.Index(fields=['sync_updated_at'], name='five9_contacts_sync_updated_at_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='five9contact',
            unique_together={('contactID', 'list_name')},
        ),
    ]
