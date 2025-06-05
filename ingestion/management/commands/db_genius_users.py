import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_UserData, Genius_Division
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone
from datetime import datetime

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download user data directly from the database and update the local database."
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="user_data",  # Changed default from "user" to "users_data"
            help="The name of the table to download data from. Defaults to 'user_data'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        connection = None

        try:
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data
            divisions = self._preload_divisions()
            
            # Process records in batches
            self._process_all_records(cursor, table_name, divisions)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _preload_divisions(self):
        """Preload divisions for lookup."""
        return {division.id: division for division in Genius_Division.objects.all()}
    
    def _process_all_records(self, cursor, table_name, divisions):
        """Process all records in batches."""
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_records = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))
        
        # Process records in batches
        for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
            self._process_batch_at_offset(cursor, table_name, offset, divisions)
    
    def _process_batch_at_offset(self, cursor, table_name, offset, divisions):
        """Process a batch of records starting at the specified offset."""
        # Get the batch of records
        cursor.execute(f"""
            SELECT user_id, division_id, title_id, manager_user_id, first_name, 
                   first_name_alt, last_name, email, personal_email, birth_date, ssn, 
                   gender_id, marital_status_id, time_zone_name, lead_radius_zip, 
                   lead_radius_distance, lead_types, lead_views_allowed, lead_call_center, 
                   google_calendar_channel_id, google_calendar_resource_id, 
                   google_calendar_sync_token, google_calendar_sync_start, 
                   google_calendar_last_sync, google_calendar_channel_expiration, 
                   project_commission_pct, hired_on, add_datetime, add_user_id, 
                   is_inactive, inactive_on, inactive_reason_id, inactive_reason_other, 
                   salary_account_id, advance_account_id, inactive_transfer_division_id, 
                   override_paychex_department_id, override_paychex_department_effective_date, 
                   google_user_error, google_user_status, start_date, user_associations_id, 
                   google_user_id
            FROM {table_name}
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        rows = cursor.fetchall()
        
        # Process the batch
        self._process_batch(rows, divisions)
    
    def _process_batch(self, rows, divisions):
        """Process a batch of user records."""
        to_create = []
        to_update = []
        existing_records = Genius_UserData.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Extract fields from row
                (
                    user_id, division_id, title_id, manager_user_id, first_name, 
                    first_name_alt, last_name, email, personal_email, birth_date, ssn, 
                    gender_id, marital_status_id, time_zone_name, lead_radius_zip, 
                    lead_radius_distance, lead_types, lead_views_allowed, lead_call_center, 
                    google_calendar_channel_id, google_calendar_resource_id, 
                    google_calendar_sync_token, google_calendar_sync_start, 
                    google_calendar_last_sync, google_calendar_channel_expiration, 
                    project_commission_pct, hired_on, add_datetime, add_user_id, 
                    is_inactive, inactive_on, inactive_reason_id, inactive_reason_other, 
                    salary_account_id, advance_account_id, inactive_transfer_division_id, 
                    override_paychex_department_id, override_paychex_department_effective_date, 
                    google_user_error, google_user_status, start_date, user_associations_id, 
                    google_user_id
                ) = row

                # Get division
                division = divisions.get(division_id) if division_id else None
                
                # Process boolean fields (tinyint)
                lead_call_center = int(lead_call_center) if lead_call_center is not None else 0
                is_inactive = int(is_inactive) if is_inactive is not None else 0
                
                # Process datetime fields
                birth_date = self._parse_date(birth_date)
                google_calendar_sync_start = self._parse_datetime(google_calendar_sync_start)
                google_calendar_last_sync = self._parse_datetime(google_calendar_last_sync)
                google_calendar_channel_expiration = self._parse_datetime(google_calendar_channel_expiration)
                hired_on = self._parse_datetime(hired_on)
                add_datetime = self._parse_datetime(add_datetime)
                inactive_on = self._parse_datetime(inactive_on)
                override_paychex_department_effective_date = self._parse_date(override_paychex_department_effective_date)
                start_date = self._parse_datetime(start_date)

                # Create or update record
                if user_id in existing_records:
                    record = self._update_record(
                        existing_records[user_id], division, title_id, manager_user_id, first_name,
                        first_name_alt, last_name, email, personal_email, birth_date, ssn,
                        gender_id, marital_status_id, time_zone_name, lead_radius_zip,
                        lead_radius_distance, lead_types, lead_views_allowed, lead_call_center,
                        google_calendar_channel_id, google_calendar_resource_id,
                        google_calendar_sync_token, google_calendar_sync_start,
                        google_calendar_last_sync, google_calendar_channel_expiration,
                        project_commission_pct, hired_on, add_datetime, add_user_id,
                        is_inactive, inactive_on, inactive_reason_id, inactive_reason_other,
                        salary_account_id, advance_account_id, inactive_transfer_division_id,
                        override_paychex_department_id, override_paychex_department_effective_date,
                        google_user_error, google_user_status, start_date, user_associations_id,
                        google_user_id
                    )
                    to_update.append(record)
                else:
                    record = self._create_record(
                        user_id, division, title_id, manager_user_id, first_name,
                        first_name_alt, last_name, email, personal_email, birth_date, ssn,
                        gender_id, marital_status_id, time_zone_name, lead_radius_zip,
                        lead_radius_distance, lead_types, lead_views_allowed, lead_call_center,
                        google_calendar_channel_id, google_calendar_resource_id,
                        google_calendar_sync_token, google_calendar_sync_start,
                        google_calendar_last_sync, google_calendar_channel_expiration,
                        project_commission_pct, hired_on, add_datetime, add_user_id,
                        is_inactive, inactive_on, inactive_reason_id, inactive_reason_other,
                        salary_account_id, advance_account_id, inactive_transfer_division_id,
                        override_paychex_department_id, override_paychex_department_effective_date,
                        google_user_error, google_user_status, start_date, user_associations_id,
                        google_user_id
                    )
                    to_create.append(record)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing record ID {row[0] if row else 'unknown'}: {e}"))

        # Save records to database
        self._save_records(to_create, to_update)
    
    def _update_record(self, record, division, title_id, manager_user_id, first_name,
                      first_name_alt, last_name, email, personal_email, birth_date, ssn,
                      gender_id, marital_status_id, time_zone_name, lead_radius_zip,
                      lead_radius_distance, lead_types, lead_views_allowed, lead_call_center,
                      google_calendar_channel_id, google_calendar_resource_id,
                      google_calendar_sync_token, google_calendar_sync_start,
                      google_calendar_last_sync, google_calendar_channel_expiration,
                      project_commission_pct, hired_on, add_datetime, add_user_id,
                      is_inactive, inactive_on, inactive_reason_id, inactive_reason_other,
                      salary_account_id, advance_account_id, inactive_transfer_division_id,
                      override_paychex_department_id, override_paychex_department_effective_date,
                      google_user_error, google_user_status, start_date, user_associations_id,
                      google_user_id):
        """Update an existing user record with only the fields that exist in the model."""
        # Only update fields that exist in the model
        record.division = division
        record.title_id = title_id
        record.manager_user_id = manager_user_id
        record.first_name = first_name
        record.first_name_alt = first_name_alt
        record.last_name = last_name
        record.email = email
        record.personal_email = personal_email
        record.birth_date = birth_date
        record.gender_id = gender_id
        record.marital_status_id = marital_status_id
        record.time_zone_name = time_zone_name
        record.hired_on = hired_on
        record.add_datetime = add_datetime
        record.add_user_id = add_user_id
        record.start_date = start_date
        # Added new fields
        record.is_inactive = bool(is_inactive)
        record.inactive_on = inactive_on
        record.inactive_reason_id = inactive_reason_id
        record.inactive_reason_other = inactive_reason_other
        
        return record
    
    def _create_record(self, user_id, division, title_id, manager_user_id, first_name,
                      first_name_alt, last_name, email, personal_email, birth_date, ssn,
                      gender_id, marital_status_id, time_zone_name, lead_radius_zip,
                      lead_radius_distance, lead_types, lead_views_allowed, lead_call_center,
                      google_calendar_channel_id, google_calendar_resource_id,
                      google_calendar_sync_token, google_calendar_sync_start,
                      google_calendar_last_sync, google_calendar_channel_expiration,
                      project_commission_pct, hired_on, add_datetime, add_user_id,
                      is_inactive, inactive_on, inactive_reason_id, inactive_reason_other,
                      salary_account_id, advance_account_id, inactive_transfer_division_id,
                      override_paychex_department_id, override_paychex_department_effective_date,
                      google_user_error, google_user_status, start_date, user_associations_id,
                      google_user_id):
        """Create a new user record with only the fields that exist in the model."""
        # Create a new record with only the fields that exist in the model
        return Genius_UserData(
            id=user_id,
            division=division,
            title_id=title_id,
            manager_user_id=manager_user_id,
            first_name=first_name,
            first_name_alt=first_name_alt,
            last_name=last_name,
            email=email,
            personal_email=personal_email,
            birth_date=birth_date,
            gender_id=gender_id,
            marital_status_id=marital_status_id,
            time_zone_name=time_zone_name,
            hired_on=hired_on,
            add_datetime=add_datetime,
            add_user_id=add_user_id,
            start_date=start_date,
            # Added new fields
            is_inactive=bool(is_inactive),
            inactive_on=inactive_on,
            inactive_reason_id=inactive_reason_id,
            inactive_reason_other=inactive_reason_other
        )
    
    def _save_records(self, to_create, to_update):
        """Save records to database with error handling."""
        try:
            if to_create:
                Genius_UserData.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
            
            if to_update:
                # List only fields that exist in the model
                fields_to_update = [
                    'division', 'title_id', 'manager_user_id', 'first_name',
                    'first_name_alt', 'last_name', 'email', 'personal_email',
                    'birth_date', 'gender_id', 'marital_status_id', 'time_zone_name',
                    'hired_on', 'add_datetime', 'add_user_id', 'start_date',
                    # Added new fields
                    'is_inactive', 'inactive_on', 'inactive_reason_id', 'inactive_reason_other'
                ]
                
                Genius_UserData.objects.bulk_update(to_update, fields_to_update, batch_size=BATCH_SIZE)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during bulk operations: {e}"))
            # Fallback to individual saves
            for record in to_create + to_update:
                try:
                    record.save()
                except Exception as individual_error:
                    self.stdout.write(self.style.ERROR(f"Error saving record {record.id}: {individual_error}"))
    
    def _parse_datetime(self, value):
        """Helper function to safely parse and make datetime timezone-aware."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return timezone.make_aware(value, dt_timezone.utc) if timezone.is_naive(value) else value
        
        return value
    
    def _parse_date(self, value):
        """Helper function to safely parse date values."""
        if value is None:
            return None
            
        if isinstance(value, datetime):
            return value.date()
            
        return value