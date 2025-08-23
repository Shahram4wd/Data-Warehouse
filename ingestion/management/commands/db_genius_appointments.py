import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_Appointment, Genius_Prospect, Genius_ProspectSource, Genius_AppointmentType, Genius_AppointmentOutcome
from ingestion.models.common import SyncHistory
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone
from datetime import datetime, date, timedelta, time
from typing import Optional

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download appointments directly from the database and update the local database."

    def add_arguments(self, parser):
        # Standard CRM sync flags according to sync_crm_guide.md
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        parser.add_argument(
            '--force-overwrite',
            action='store_true', 
            help='Completely replace existing records'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Manual sync start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test run without database writes'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            default=0,
            help='Limit total records (0 = unlimited)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable verbose logging'
        )
        
        # Genius-specific arguments (backward compatibility)
        parser.add_argument(
            '--start-date',
            type=str,
            help='(DEPRECATED) Use --since instead. Start date for sync (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for sync (YYYY-MM-DD format)'
        )
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
        # Setup debug logging if requested
        if options.get('debug'):
            import logging
            logging.getLogger().setLevel(logging.DEBUG)
            
        table_name = options["table"]
        start_offset = options["start_offset"]
        start_page = options["page"]
        dry_run = options.get("dry_run", False)
        debug = options.get("debug", False)
        max_records = options.get("max_records", 0)
        connection = None
        
        # Parse date arguments following CRM sync guide priority
        since_date = self._parse_since_parameter(options)
        end_date = self._parse_date_parameter(options.get('end_date'))
        force_overwrite = options.get('force_overwrite', False)
        full_sync = options.get('full', False)
        
        # Initialize counters
        self.corrupted_count = 0
        self.processed_count = 0
        self.dry_run = dry_run
        self.debug = debug
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes will be made"))
        if debug:
            self.stdout.write(self.style.SUCCESS("🐛 DEBUG MODE - Verbose logging enabled"))

        # Create SyncHistory record
        sync_record = self._create_sync_record() if not dry_run else None

        try:
            # Database connection and preloading data
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data for better performance
            lookup_data = self._preload_lookup_data(cursor)
            
            # Determine sync strategy and build query
            sync_strategy = self._determine_sync_strategy(since_date, force_overwrite, full_sync)
            where_clause = self._build_where_clause(sync_strategy['since_date'], end_date)
            
            # Get total records and process in batches
            count_query = f"SELECT COUNT(*) FROM {table_name}{where_clause}"
            cursor.execute(count_query)
            total_records = cursor.fetchone()[0]
            
            if max_records > 0 and max_records < total_records:
                total_records = max_records
                self.stdout.write(f"Limiting to {max_records} records (--max-records)")
            
            self.stdout.write(self.style.SUCCESS(f"Total records to process from table '{table_name}': {total_records:,}"))
            
            if sync_strategy['since_date']:
                self.stdout.write(f"Delta sync since: {sync_strategy['since_date'].strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                self.stdout.write("Full sync (no timestamp filter)")
            
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
                # Build main query with delta sync filtering
                main_query = f"""
                    SELECT a.id, a.prospect_id, a.prospect_source_id, a.user_id, a.type_id, a.date, a.time, a.duration, 
                           a.address1, a.address2, a.city, a.state, a.zip, a.email, a.notes, a.add_user_id, a.add_date, 
                           a.assign_date, a.confirm_user_id, a.confirm_date, a.confirm_with, a.spouses_present, 
                           a.is_complete, a.complete_outcome_id, a.complete_user_id, a.complete_date, a.marketsharp_id, 
                           a.marketsharp_appt_type, a.leap_estimate_id, a.updated_at, a.third_party_source_id, tps.third_party_id AS hubspot_appointment_id
                    FROM {table_name} AS a
                    LEFT JOIN third_party_source AS tps 
                      ON tps.id = a.third_party_source_id
                    LEFT JOIN third_party_source_type AS tpst 
                      ON tpst.id = tps.third_party_source_type_id AND tpst.label = 'hubspot'
                    {where_clause}
                    LIMIT {BATCH_SIZE} OFFSET {offset}
                """
                cursor.execute(main_query)
                rows = cursor.fetchall()
                self._process_batch(rows, **lookup_data)
                
                # Apply max_records limit if specified
                if max_records > 0 and self.processed_count >= max_records:
                    self.stdout.write(f"Reached max records limit: {max_records}")
                    break
                
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
            # Print summary
            if dry_run:
                if self.corrupted_count > 0:
                    self.stdout.write(self.style.WARNING(f"DRY RUN Summary: {self.processed_count} records would be processed, {self.corrupted_count} records had corrupted data that would be cleaned (no database changes made)."))
                else:
                    self.stdout.write(self.style.WARNING(f"DRY RUN Summary: {self.processed_count} records would be processed successfully with no data corruption detected (no database changes made)."))
            else:
                if self.corrupted_count > 0:
                    self.stdout.write(self.style.WARNING(f"Summary: {self.processed_count} records processed, {self.corrupted_count} records had corrupted data that was cleaned."))
                else:
                    self.stdout.write(self.style.SUCCESS(f"Summary: {self.processed_count} records processed successfully with no data corruption detected."))
            
            # Update SyncHistory on success
            if sync_record and not dry_run:
                self._complete_sync_record(sync_record, 'success')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
            # Update SyncHistory on failure
            if sync_record and not dry_run:
                self._complete_sync_record(sync_record, 'failed', str(e))
            raise
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _parse_since_parameter(self, options) -> Optional[datetime]:
        """Parse --since parameter following CRM sync guide priority order."""
        # Priority order:
        # 1. --since parameter (manual override)
        # 2. --start-date parameter (backward compatibility)
        # 3. SyncHistory table last successful sync timestamp
        # 4. Default: None (full sync)
        
        since_param = options.get('since')
        start_date_param = options.get('start_date')  # Backward compatibility
        
        if since_param:
            return self._parse_date_parameter(since_param)
        elif start_date_param:
            self.stdout.write(self.style.WARNING('--start-date is deprecated, use --since instead'))
            return self._parse_date_parameter(start_date_param)
        
        return None
    
    def _parse_date_parameter(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        
        try:
            # Parse YYYY-MM-DD format
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            # Convert to UTC timezone-aware datetime
            return date_obj.replace(tzinfo=dt_timezone.utc)
        except ValueError:
            self.stdout.write(self.style.ERROR(f'Invalid date format "{date_str}". Use YYYY-MM-DD format.'))
            return None
    
    def _get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get last successful sync timestamp from SyncHistory."""
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source='genius',
                sync_type='appointments',
                status='success'
            ).order_by('-end_time').first()
            
            return last_sync.end_time if last_sync else None
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not retrieve last sync timestamp: {e}"))
            return None
    
    def _determine_sync_strategy(self, since_param: Optional[datetime], force_overwrite: bool, full_sync: bool) -> dict:
        """Determine sync strategy following CRM sync guide."""
        if force_overwrite or full_sync:
            # Force full sync
            return {
                'since_date': None,
                'strategy': 'full',
                'description': 'Full sync (force overwrite)' if force_overwrite else 'Full sync'
            }
        elif since_param:
            # Manual override timestamp
            return {
                'since_date': since_param,
                'strategy': 'delta',
                'description': f'Delta sync since {since_param.strftime("%Y-%m-%d")}'
            }
        else:
            # Check SyncHistory for last successful sync
            last_sync = self._get_last_sync_timestamp()
            return {
                'since_date': last_sync,
                'strategy': 'delta' if last_sync else 'full',
                'description': f'Delta sync since last successful sync ({last_sync.strftime("%Y-%m-%d %H:%M:%S")})' if last_sync else 'Full sync (no previous sync found)'
            }
    
    def _build_where_clause(self, since_date: Optional[datetime], end_date: Optional[datetime]) -> str:
        """Build WHERE clause for delta sync filtering."""
        conditions = []
        
        if since_date:
            # Use updated_at for appointments (consistent with prospects command)
            since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
            conditions.append(f"a.updated_at > '{since_str}'")
        
        if end_date:
            end_str = end_date.strftime('%Y-%m-%d %H:%M:%S') 
            conditions.append(f"a.updated_at <= '{end_str}'")
        
        if conditions:
            return ' WHERE ' + ' AND '.join(conditions)
        return ''
    
    def _create_sync_record(self) -> SyncHistory:
        """Create SyncHistory record for tracking."""
        return SyncHistory.objects.create(
            crm_source='genius',
            sync_type='appointments',
            status='running',
            start_time=timezone.now(),
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_failed=0,
            configuration={
                'batch_size': BATCH_SIZE,
                'command': 'db_genius_appointments'
            }
        )
    
    def _complete_sync_record(self, sync_record: SyncHistory, status: str, error_message: str = None):
        """Complete SyncHistory record with final status."""
        sync_record.status = status
        sync_record.end_time = timezone.now()
        sync_record.records_processed = self.processed_count
        sync_record.records_failed = self.corrupted_count
        
        if error_message:
            sync_record.error_message = error_message
        
        # Calculate performance metrics
        if sync_record.start_time and sync_record.end_time:
            duration = (sync_record.end_time - sync_record.start_time).total_seconds()
            sync_record.performance_metrics = {
                'duration_seconds': duration,
                'records_per_second': self.processed_count / duration if duration > 0 else 0,
                'corrupted_records': self.corrupted_count
            }
        
        sync_record.save()
    
    def _preload_lookup_data(self, cursor):
        """Preload all lookup data needed for processing."""
        # Load related model data
        prospects = {prospect.id: prospect for prospect in Genius_Prospect.objects.all()}
        prospect_sources = {source.id: source for source in Genius_ProspectSource.objects.all()}
        appointment_types = {appt_type.id: appt_type for appt_type in Genius_AppointmentType.objects.all()}
        appointment_outcomes = {outcome.id: outcome for outcome in Genius_AppointmentOutcome.objects.all()}
        
        return {
            'prospects': prospects,
            'prospect_sources': prospect_sources,
            'appointment_types': appointment_types,
            'appointment_outcomes': appointment_outcomes
        }
    
    def _process_batch(self, rows, prospects, prospect_sources, appointment_types, 
                      appointment_outcomes):
        """Process a batch of appointment records."""
        to_create = []
        to_update = []
        existing_records = Genius_Appointment.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Validate row length first
                if len(row) != 32:  # Updated to 32 columns (added updated_at)
                    self.stdout.write(self.style.WARNING(f"Row has {len(row)} columns, expected 32. Skipping record."))
                    continue
                
                # Extract fields from row with debugging
                try:
                    (
                        record_id, prospect_id, prospect_source_id, user_id, type_id, date, time, duration,
                        address1, address2, city, state, zip, email, notes, add_user_id, add_date,
                        assign_date, confirm_user_id, confirm_date, confirm_with, spouses_present, 
                        is_complete, complete_outcome_id, complete_user_id, complete_date,
                        marketsharp_id, marketsharp_appt_type, leap_estimate_id, updated_at, third_party_source_id, 
                        hubspot_appointment_id
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
                
                # The hubspot_appointment_id is already resolved by the SQL JOIN
                # No additional lookup needed since the JOIN handles the mapping
                hubspot_id = hubspot_appointment_id

                # Increment processed count
                self.processed_count += 1
                
                if self.debug:
                    if hubspot_id:
                        self.stdout.write(f"📝 DEBUG: Processing appointment {record_id} for prospect {prospect_id} (Type: {type_id}, HubSpot: {hubspot_id}, Third Party Source: {third_party_source_id})")
                    else:
                        self.stdout.write(f"📝 DEBUG: Processing appointment {record_id} for prospect {prospect_id} (Type: {type_id}, No HubSpot ID)")

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
                    updated_at, spouses_present, is_complete, original_row=row
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
        if not self.dry_run:
            self._save_records(to_create, to_update)
        else:
            # In dry run mode, just show what would be saved
            if to_create:
                self.stdout.write(self.style.WARNING(f"DRY RUN: Would create {len(to_create)} new appointment records"))
                if self.debug:
                    for record in to_create[:5]:  # Show first 5 records in debug mode
                        self.stdout.write(f"  🆕 Would create: Appointment {record.id} for prospect {record.prospect_id}")
                    if len(to_create) > 5:
                        self.stdout.write(f"  ... and {len(to_create) - 5} more records")
            
            if to_update:
                self.stdout.write(self.style.WARNING(f"DRY RUN: Would update {len(to_update)} existing appointment records"))
                if self.debug:
                    for record in to_update[:5]:  # Show first 5 records in debug mode
                        self.stdout.write(f"  ♻️  Would update: Appointment {record.id} for prospect {record.prospect_id}")
                    if len(to_update) > 5:
                        self.stdout.write(f"  ... and {len(to_update) - 5} more records")
    
    def _process_field_values(self, date_val, time_val, duration_val, add_date, assign_date, 
                             confirm_date, complete_date, updated_at, spouses_present, is_complete, original_row=None):
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
        updated_at = self._parse_datetime(updated_at)
        
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
            'complete_date': complete_date,
            'updated_at': updated_at,
            'spouses_present': spouses_present,
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
        
        # Set updated_at from source database
        record.updated_at = processed_data['updated_at']
        
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
        record.hubspot_appointment_id = self._safe_int_convert(hubspot_id, is_bigint=True, field_name="hubspot_appointment_id", original_row=original_row)
        
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
            hubspot_appointment_id=self._safe_int_convert(hubspot_id, is_bigint=True, field_name="hubspot_appointment_id", original_row=original_row),
            updated_at=processed_data['updated_at']
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
                        'hubspot_appointment_id', 'updated_at'
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
