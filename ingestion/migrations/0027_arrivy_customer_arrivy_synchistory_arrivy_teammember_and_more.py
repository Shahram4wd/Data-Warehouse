# Generated by Django 4.2.23 on 2025-06-18 18:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0026_alter_genius_appointment_complete_user_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Arrivy_Customer',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('external_id', models.CharField(blank=True, max_length=255, null=True)),
                ('company_name', models.CharField(blank=True, max_length=255, null=True)),
                ('first_name', models.CharField(blank=True, max_length=255, null=True)),
                ('last_name', models.CharField(blank=True, max_length=255, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('mobile_number', models.CharField(blank=True, max_length=20, null=True)),
                ('address_line_1', models.CharField(blank=True, max_length=255, null=True)),
                ('address_line_2', models.CharField(blank=True, max_length=255, null=True)),
                ('city', models.CharField(blank=True, max_length=100, null=True)),
                ('state', models.CharField(blank=True, max_length=100, null=True)),
                ('country', models.CharField(blank=True, max_length=100, null=True)),
                ('zipcode', models.CharField(blank=True, max_length=20, null=True)),
                ('timezone', models.CharField(blank=True, max_length=50, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('extra_fields', models.JSONField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_time', models.DateTimeField(blank=True, null=True)),
                ('updated_time', models.DateTimeField(blank=True, null=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Arrivy Customer',
                'verbose_name_plural': 'Arrivy Customers',
                'db_table': 'arrivy_customer',
            },
        ),
        migrations.CreateModel(
            name='Arrivy_SyncHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('endpoint', models.CharField(max_length=100, unique=True)),
                ('last_synced_at', models.DateTimeField()),
                ('total_records', models.IntegerField(default=0)),
                ('success_count', models.IntegerField(default=0)),
                ('error_count', models.IntegerField(default=0)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Arrivy Sync History',
                'verbose_name_plural': 'Arrivy Sync Histories',
                'db_table': 'arrivy_sync_history',
            },
        ),
        migrations.CreateModel(
            name='Arrivy_TeamMember',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('external_id', models.CharField(blank=True, max_length=255, null=True)),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('first_name', models.CharField(blank=True, max_length=255, null=True)),
                ('last_name', models.CharField(blank=True, max_length=255, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('image_path', models.URLField(blank=True, null=True)),
                ('image_id', models.CharField(blank=True, max_length=50, null=True)),
                ('username', models.CharField(blank=True, max_length=255, null=True)),
                ('role', models.CharField(blank=True, max_length=100, null=True)),
                ('permission', models.CharField(blank=True, max_length=100, null=True)),
                ('group_id', models.CharField(blank=True, max_length=50, null=True)),
                ('group_name', models.CharField(blank=True, max_length=255, null=True)),
                ('timezone', models.CharField(blank=True, max_length=50, null=True)),
                ('address', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_online', models.BooleanField(default=False)),
                ('can_turnon_location', models.BooleanField(default=False)),
                ('support_sms', models.BooleanField(default=True)),
                ('support_phone', models.BooleanField(default=True)),
                ('created_time', models.DateTimeField(blank=True, null=True)),
                ('updated_time', models.DateTimeField(blank=True, null=True)),
                ('last_location_time', models.DateTimeField(blank=True, null=True)),
                ('extra_fields', models.JSONField(blank=True, null=True)),
                ('skills', models.JSONField(blank=True, null=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Arrivy Team Member',
                'verbose_name_plural': 'Arrivy Team Members',
                'db_table': 'arrivy_team_member',
            },
        ),
        migrations.CreateModel(
            name='Arrivy_Booking',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('external_id', models.CharField(blank=True, max_length=255, null=True)),
                ('title', models.CharField(blank=True, max_length=500, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('details', models.TextField(blank=True, null=True)),
                ('start_datetime', models.DateTimeField(blank=True, null=True)),
                ('end_datetime', models.DateTimeField(blank=True, null=True)),
                ('start_datetime_original_iso_str', models.CharField(blank=True, max_length=50, null=True)),
                ('end_datetime_original_iso_str', models.CharField(blank=True, max_length=50, null=True)),
                ('timezone', models.CharField(blank=True, max_length=50, null=True)),
                ('status', models.CharField(blank=True, max_length=50, null=True)),
                ('status_id', models.IntegerField(blank=True, null=True)),
                ('task_type', models.CharField(blank=True, max_length=100, null=True)),
                ('address_line_1', models.CharField(blank=True, max_length=255, null=True)),
                ('address_line_2', models.CharField(blank=True, max_length=255, null=True)),
                ('city', models.CharField(blank=True, max_length=100, null=True)),
                ('state', models.CharField(blank=True, max_length=100, null=True)),
                ('country', models.CharField(blank=True, max_length=100, null=True)),
                ('zipcode', models.CharField(blank=True, max_length=20, null=True)),
                ('exact_location', models.JSONField(blank=True, null=True)),
                ('assigned_team_members', models.JSONField(blank=True, null=True)),
                ('team_member_ids', models.TextField(blank=True, null=True)),
                ('template_id', models.CharField(blank=True, max_length=50, null=True)),
                ('template_extra_fields', models.JSONField(blank=True, null=True)),
                ('extra_fields', models.JSONField(blank=True, null=True)),
                ('custom_fields', models.JSONField(blank=True, null=True)),
                ('actual_start_datetime', models.DateTimeField(blank=True, null=True)),
                ('actual_end_datetime', models.DateTimeField(blank=True, null=True)),
                ('duration_estimate', models.IntegerField(blank=True, null=True)),
                ('is_recurring', models.BooleanField(default=False)),
                ('is_all_day', models.BooleanField(default=False)),
                ('enable_time_window_display', models.BooleanField(default=False)),
                ('unscheduled', models.BooleanField(default=False)),
                ('notifications', models.JSONField(blank=True, null=True)),
                ('created_time', models.DateTimeField(blank=True, null=True)),
                ('updated_time', models.DateTimeField(blank=True, null=True)),
                ('synced_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bookings', to='ingestion.arrivy_customer')),
            ],
            options={
                'verbose_name': 'Arrivy Booking',
                'verbose_name_plural': 'Arrivy Bookings',
                'db_table': 'arrivy_booking',
            },
        ),
    ]
