import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_Appointment, Genius_Prospect, Genius_ProspectSource, Genius_AppointmentType, Genius_AppointmentOutcome
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone
from datetime import datetime, date, timedelta, time

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download appointments directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="appointment",
            help="The name of the table to download data from. Defaults to 'appointment'."
        )
        parser.add_argument(
            "--start-offset",
            type=int,
            default=0,
            help="The starting offset for processing records. Defaults to 0."
        )
        parser.add_argument(
            "--page",
            type=int,
            default=1,
            help="Starting page number (each page is BATCH_SIZE records). Defaults to 1. Overrides --start-offset if provided."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        start_offset = options["start_offset"]
        start_page = options["page"]
        connection = None
        
        # Initialize counters
        self.corrupted_count = 0
        self.processed_count = 0

        try:
            # Database connection and preloading data
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data for better performance
            lookup_data = self._preload_lookup_data(cursor)
            
            # Get total records and process in batches
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_records = cursor.fetchone()[0]
            self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))
            
            # Calculate starting offset based on page number (page overrides start_offset if provided)
            if start_page > 1:
                start_offset = (start_page - 1) * BATCH_SIZE
                remaining_records = total_records - start_offset
                
                if start_offset >= total_records:
                    self.stdout.write(self.style.WARNING(f"Starting page {start_page} is beyond available data. Total records: {total_records}"))
                    return
                
                self.stdout.write(f"Starting from page {start_page} (offset {start_offset:,}), processing {remaining_records:,} remaining records")
            else:
                remaining_records = total_records - start_offset
                if start_offset > 0:
                    self.stdout.write(f"Starting from offset {start_offset:,}, processing {remaining_records:,} remaining records")
            
            # Process records in batches starting from the calculated offset
            for offset in tqdm(range(start_offset, total_records, BATCH_SIZE), desc="Processing batches"):
                cursor.execute(f"""
                    SELECT id, prospect_id, prospect_source_id, user_id, type_id, date, time, duration, address1, address2, city, state, zip, email, notes, add_user_id, add_date, assign_date, confirm_user_id, confirm_date, confirm_with, spouses_present, is_complete, complete_outcome_id, complete_user_id, complete_date, marketsharp_id, marketsharp_appt_type, leap_estimate_id, third_party_source_id
                    FROM appointment
                    LIMIT {BATCH_SIZE} OFFSET {offset}
                """)
                rows = cursor.fetchall()
                self._process_batch(rows, **lookup_data)
                
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
            # Print summary
            if self.corrupted_count > 0:
                self.stdout.write(self.style.WARNING(f"Summary: {self.processed_count} records processed, {self.corrupted_count} records had corrupted data that was cleaned."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Summary: {self.processed_count} records processed successfully with no data corruption detected."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _preload_lookup_data(self, cursor):
        """Preload all lookup data needed for processing."""
        # Load related model data
        prospects = {prospect.id: prospect for prospect in Genius_Prospect.objects.all()}
        prospect_sources = {source.id: source for source in Genius_ProspectSource.objects.all()}
        appointment_types = {appt_type.id: appt_type for appt_type in Genius_AppointmentType.objects.all()}
        appointment_outcomes = {outcome.id: outcome for outcome in Genius_AppointmentOutcome.objects.all()}
        
        # Load Hubspot source IDs
        cursor.execute("""
            SELECT tps.id, tps.third_party_id
            FROM third_party_source AS tps
            LEFT JOIN third_party_source_type AS tpst ON tps.third_party_source_type_id = tpst.id
            WHERE tpst.label = "hubspot"
        """)
        hubspot_sources = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            'prospects': prospects,
            'prospect_sources': prospect_sources,
            'appointment_types': appointment_types,
            'appointment_outcomes': appointment_outcomes,
            'hubspot_sources': hubspot_sources
        }
    
    def _process_batch(self, rows, prospects, prospect_sources, appointment_types, 
                      appointment_outcomes, hubspot_sources):
        """Process a batch of appointment records."""
        to_create = []
        to_update = []
        existing_records = Genius_Appointment.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Validate row length first
                if len(row) != 30:  # Expected number of columns
                    self.stdout.write(self.style.WARNING(f"Row has {len(row)} columns, expected 30. Skipping record."))
                    continue
                
                # Extract fields from row with debugging
                try:
                    (
                        record_id, prospect_id, prospect_source_id, user_id, type_id, date, time, duration,
                        address1, address2, city, state, zip, email, notes, add_user_id, add_date,
                        assign_date, confirm_user_id, confirm_date, confirm_with, spouses_present,
                        is_complete, complete_outcome_id, complete_user_id, complete_date,
                        marketsharp_id, marketsharp_appt_type, leap_estimate_id, third_party_source_id
                    ) = row
                except ValueError as e:
                    self.stdout.write(self.style.ERROR(f"Error unpacking row for record_id {row[0] if row else 'unknown'}: {e}"))
                    self.stdout.write(self.style.ERROR(f"Row data: {row}"))
                    continue

                # Look up related objects
                prospect = prospects.get(prospect_id)
                prospect_source = prospect_sources.get(prospect_source_id)
                appointment_type = appointment_types.get(type_id)
                complete_outcome = appointment_outcomes.get(complete_outcome_id)
                hubspot_id = hubspot_sources.get(third_party_source_id) if third_party_source_id is not None else None

                # Increment processed count
                self.processed_count += 1

                # Skip records with missing required foreign keys
                if not prospect:
                    self.stdout.write(self.style.WARNING(f"Skipping appointment {record_id}: prospect {prospect_id} not found"))
                    self.stdout.write(self.style.WARNING(f"Original row data: {row}"))
                    continue
                    
                if not appointment_type:
                    self.stdout.write(self.style.WARNING(f"Skipping appointment {record_id}: appointment type {type_id} not found"))
                    self.stdout.write(self.style.WARNING(f"Original row data: {row}"))
                    continue

                # Process fields that need special handling
                processed_data = self._process_field_values(
                    date, time, duration, add_date, assign_date, confirm_date, complete_date,
                    spouses_present, is_complete, original_row=row
                )
                
                # Create or update the record
                if record_id in existing_records:
                    record = existing_records[record_id]
                    self._update_record(record, prospect, prospect_source, user_id, appointment_type,
                                       processed_data, address1, address2, city, state, zip, email, notes,
                                       add_user_id, confirm_user_id, confirm_with, complete_outcome,
                                       complete_user_id, marketsharp_id, marketsharp_appt_type,
                                       leap_estimate_id, hubspot_id, original_row=row)
                    to_update.append(record)
                else:
                    record = self._create_record(record_id, prospect, prospect_source, user_id, appointment_type,
                                               processed_data, address1, address2, city, state, zip, email, notes,
                                               add_user_id, confirm_user_id, confirm_with, complete_outcome,
                                               complete_user_id, marketsharp_id, marketsharp_appt_type,
                                               leap_estimate_id, hubspot_id, original_row=row)
                    to_create.append(record)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing record ID {row[0] if row else 'unknown'}: {e}"))

        # Save records to database
        self._save_records(to_create, to_update)
    
    def _process_field_values(self, date_val, time_val, duration_val, add_date, assign_date, 
                             confirm_date, complete_date, spouses_present, is_complete, original_row=None):
        """Process and convert field values to appropriate types."""
        # Process date and time fields
        if isinstance(date_val, datetime):
            date_val = date_val.date()
        
        if isinstance(time_val, timedelta):
            total_seconds = time_val.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            time_val = time(hours, minutes, seconds)
        
        # Process datetime fields
        add_date = self._parse_datetime(add_date)
        assign_date = self._parse_datetime(assign_date)
        confirm_date = self._parse_datetime(confirm_date)
        complete_date = self._parse_datetime(complete_date)
        
        # Process boolean fields as integers with validation
        spouses_present = self._safe_int_convert(spouses_present, 0, field_name="spouses_present", original_row=original_row)
        is_complete = self._safe_int_convert(is_complete, 0, field_name="is_complete", original_row=original_row)
        
        return {
            'date': date_val,
            'time': time_val,
            'duration': duration_val,
            'add_date': add_date,
            'assign_date': assign_date,
            'confirm_date': confirm_date,
            'complete_date': complete_date,            'spouses_present': spouses_present,
            'is_complete': is_complete
        }

    def _safe_string_convert(self, value, default=None):
        """Safely convert value to string, handling large integers."""
        if value is None:
            return default
        
        try:
            # Convert to string, handling large integers that might be too big for integer fields
            return str(value)
        except (ValueError, TypeError):
            self.stdout.write(self.style.WARNING(f"Invalid string value: {value}, using default {default}"))
            return default

    def _safe_int_convert(self, value, default=None, is_bigint=False, field_name="unknown", original_row=None):
        """Safely convert value to integer with range validation."""
        if value is None:
            return default
        
        try:
            int_val = int(value)
            
            if is_bigint:
                # Check for PostgreSQL bigint range (-9223372036854775808 to 9223372036854775807)
                if int_val < -9223372036854775808 or int_val > 9223372036854775807:
                    self.stdout.write(self.style.WARNING(f"BigInteger out of range for {field_name}: {int_val}, using default {default}"))
                    if original_row:
                        self.stdout.write(self.style.WARNING(f"Original row data: {original_row}"))
                    self.corrupted_count += 1
                    return default
            else:
                # Check for PostgreSQL int4 range
                if int_val < -2147483648 or int_val > 2147483647:
                    self.stdout.write(self.style.WARNING(f"Integer out of range for {field_name}: {int_val}, using default {default}"))
                    if original_row:
                        self.stdout.write(self.style.WARNING(f"Original row data: {original_row}"))
                    self.corrupted_count += 1
                    return default
            
            return int_val
        except (ValueError, TypeError):
            self.stdout.write(self.style.WARNING(f"Invalid integer value for {field_name}: {value}, using default {default}"))
            if original_row:
                self.stdout.write(self.style.WARNING(f"Original row data: {original_row}"))
            self.corrupted_count += 1
            return default

    def _update_record(self, record, prospect, prospect_source, user_id, appointment_type,
                      processed_data, address1, address2, city, state, zip, email, notes,
                      add_user_id, confirm_user_id, confirm_with, complete_outcome,
                      complete_user_id, marketsharp_id, marketsharp_appt_type,
                      leap_estimate_id, hubspot_id, original_row=None):
        """Update an existing record with new values."""
        # Set foreign keys
        record.prospect = prospect
        record.prospect_source = prospect_source
        record.type = appointment_type
        record.complete_outcome = complete_outcome
        
        # Set processed fields
        record.date = processed_data['date']
        record.time = processed_data['time']
        record.duration = processed_data['duration']
        record.add_date = processed_data['add_date']
        record.assign_date = processed_data['assign_date']
        record.confirm_date = processed_data['confirm_date']
        record.complete_date = processed_data['complete_date']
        record.spouses_present = processed_data['spouses_present']
        record.is_complete = processed_data['is_complete']
        
        # Set other fields with validation
        record.user_id = self._safe_int_convert(user_id, is_bigint=True, field_name="user_id", original_row=original_row)
        record.address1 = address1
        record.address2 = address2
        record.city = city
        record.state = state
        record.zip = zip
        record.email = email
        record.notes = notes
        record.add_user_id = self._safe_int_convert(add_user_id, is_bigint=True, field_name="add_user_id", original_row=original_row)
        record.confirm_user_id = self._safe_int_convert(confirm_user_id, is_bigint=True, field_name="confirm_user_id", original_row=original_row)
        record.confirm_with = confirm_with
        record.complete_user_id = self._safe_int_convert(complete_user_id, is_bigint=True, field_name="complete_user_id", original_row=original_row)
        record.marketsharp_id = marketsharp_id
        record.marketsharp_appt_type = marketsharp_appt_type
        record.leap_estimate_id = self._safe_string_convert(leap_estimate_id)
        record.third_party_source_id = self._safe_int_convert(hubspot_id, is_bigint=True, field_name="third_party_source_id", original_row=original_row)
        
        return record
    
    def _create_record(self, record_id, prospect, prospect_source, user_id, appointment_type,
                      processed_data, address1, address2, city, state, zip, email, notes,
                      add_user_id, confirm_user_id, confirm_with, complete_outcome,
                      complete_user_id, marketsharp_id, marketsharp_appt_type,
                      leap_estimate_id, hubspot_id, original_row=None):
        """Create a new appointment record."""
        return Genius_Appointment(
            id=record_id,
            prospect=prospect,
            prospect_source=prospect_source,
            user_id=self._safe_int_convert(user_id, is_bigint=True, field_name="user_id", original_row=original_row),
            type=appointment_type,
            date=processed_data['date'],
            time=processed_data['time'],
            duration=processed_data['duration'],
            address1=address1,
            address2=address2,
            city=city,
            state=state,
            zip=zip,
            email=email,
            notes=notes,
            add_user_id=self._safe_int_convert(add_user_id, is_bigint=True, field_name="add_user_id", original_row=original_row),
            add_date=processed_data['add_date'],
            assign_date=processed_data['assign_date'],
            confirm_user_id=self._safe_int_convert(confirm_user_id, is_bigint=True, field_name="confirm_user_id", original_row=original_row),
            confirm_date=processed_data['confirm_date'],
            confirm_with=confirm_with,
            spouses_present=processed_data['spouses_present'],
            is_complete=processed_data['is_complete'],
            complete_outcome=complete_outcome,
            complete_user_id=self._safe_int_convert(complete_user_id, is_bigint=True, field_name="complete_user_id", original_row=original_row),
            complete_date=processed_data['complete_date'],
            marketsharp_id=marketsharp_id,
            marketsharp_appt_type=marketsharp_appt_type,
            leap_estimate_id=self._safe_string_convert(leap_estimate_id),
            third_party_source_id=self._safe_int_convert(hubspot_id, is_bigint=True, field_name="third_party_source_id", original_row=original_row)
        )
    
    def _save_records(self, to_create, to_update):
        """Save records to database with error handling."""
        try:
            if to_create:
                Genius_Appointment.objects.bulk_create(to_create, batch_size=BATCH_SIZE, ignore_conflicts=True)
            
            if to_update:
                Genius_Appointment.objects.bulk_update(
                    to_update,
                    [
                        'prospect', 'prospect_source', 'user_id', 'type', 'date', 'time', 'duration',
                        'address1', 'address2', 'city', 'state', 'zip', 'email', 'notes', 'add_user_id',
                        'add_date', 'assign_date', 'confirm_user_id', 'confirm_date', 'confirm_with',
                        'spouses_present', 'is_complete', 'complete_outcome', 'complete_user_id',
                        'complete_date', 'marketsharp_id', 'marketsharp_appt_type', 'leap_estimate_id',
                        'third_party_source_id'
                    ],
                    batch_size=BATCH_SIZE
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during bulk operations: {e}"))
            self._fallback_individual_saves(to_create + to_update)
    
    def _fallback_individual_saves(self, records):
        """Fallback to individual saves when bulk operations fail."""
        for record in records:
            try:
                # Additional validation before saving
                if not record.prospect:
                    self.stdout.write(self.style.WARNING(f"Skipping record {record.id}: missing prospect"))
                    continue
                if not record.type:
                    self.stdout.write(self.style.WARNING(f"Skipping record {record.id}: missing appointment type"))
                    continue
                    
                record.save()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving record {record.id}: {e}"))
    
    def _parse_datetime(self, value):
        """Helper function to safely parse and make datetime timezone-aware."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return timezone.make_aware(value, dt_timezone.utc) if timezone.is_naive(value) else value
        
        if isinstance(value, date) and not isinstance(value, datetime):
            dt = datetime.combine(value, datetime.min.time())
            return timezone.make_aware(dt, dt_timezone.utc)
        
        if isinstance(value, str):
            try:
                dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                return timezone.make_aware(dt, dt_timezone.utc)
            except ValueError:
                try:
                    dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
                    return timezone.make_aware(dt, dt_timezone.utc)
                except ValueError:
                    return None
        
        return None
