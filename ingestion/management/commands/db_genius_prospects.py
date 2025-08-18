import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_Prospect, Genius_Division, SyncHistory
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import datetime, timezone as dt_timezone

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download prospects directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="prospect",
            help="The name of the table to download data from. Defaults to 'prospect'."
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
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without making any database changes. Shows what would be processed."
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug mode with verbose logging and detailed output."
        )
        # Delta sync arguments
        parser.add_argument(
            "--since",
            type=str,
            help="Sync records modified since this timestamp (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD). Manual override for sync timestamp."
        )
        parser.add_argument(
            "--force-overwrite",
            action="store_true", 
            help="Force overwrite all records regardless of last sync timestamp. Takes precedence over --since."
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform full sync of all records. Equivalent to --force-overwrite."
        )
        parser.add_argument(
            "--start-date",
            type=str,
            help="Start date for filtering records (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD). Alias for --since."
        )
        parser.add_argument(
            "--end-date", 
            type=str,
            help="End date for filtering records (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD). Filters records updated before this date."
        )
        parser.add_argument(
            "--max-records",
            type=int,
            help="Maximum number of records to process in this sync run."
        )
    
    def handle(self, *args, **options):
        table_name = options["table"]
        start_offset = options["start_offset"]
        start_page = options["page"]
        dry_run = options.get("dry_run", False)
        debug = options.get("debug", False)
        max_records = options.get("max_records")
        end_date = options.get("end_date")
        connection = None
        sync_record = None
        
        # Initialize counters
        self.processed_count = 0
        self.dry_run = dry_run
        self.debug = debug
        
        # Determine sync strategy
        sync_strategy, sync_timestamp = self._determine_sync_strategy(options)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes will be made"))
        if debug:
            self.stdout.write(self.style.SUCCESS("🐛 DEBUG MODE - Verbose logging enabled"))
        
        # Display sync strategy
        if sync_strategy == 'incremental' and sync_timestamp:
            self.stdout.write(self.style.SUCCESS(f"📅 INCREMENTAL SYNC - Processing records updated since {sync_timestamp}"))
        else:
            self.stdout.write(self.style.SUCCESS("🔄 FULL SYNC - Processing all records"))
        
        if max_records:
            self.stdout.write(self.style.SUCCESS(f"📊 MAX RECORDS - Limited to {max_records:,} records"))
        
        if end_date:
            self.stdout.write(self.style.SUCCESS(f"📅 END DATE - Processing records updated before {end_date}"))

        try:
            # Create sync record for tracking (skip in dry-run mode)
            if not dry_run:
                sync_record = self._create_sync_record()
                
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data
            lookups = self._preload_lookup_data(cursor)
            
            # Process records in batches
            self._process_all_records(cursor, table_name, lookups, start_offset, start_page, 
                                    sync_strategy, sync_timestamp, end_date, max_records)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
            # Complete sync record
            if sync_record and not dry_run:
                self._complete_sync_record(sync_record, self.processed_count)
            
            # Print summary
            if dry_run:
                self.stdout.write(self.style.WARNING(f"DRY RUN Summary: {self.processed_count} records would be processed (no database changes made)."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Summary: {self.processed_count} records processed successfully."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
            # Mark sync as failed
            if sync_record and not dry_run:
                self._complete_sync_record(sync_record, self.processed_count, 'failed')
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _parse_since_parameter(self, since_str):
        """Parse --since parameter to datetime object."""
        if not since_str:
            return None
            
        # Try different datetime formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                naive_dt = datetime.strptime(since_str, fmt)
                return timezone.make_aware(naive_dt)
            except ValueError:
                continue
                
        raise ValueError(f"Invalid datetime format: {since_str}. Use YYYY-MM-DD HH:MM:SS or YYYY-MM-DD")
    
    def _get_last_sync_timestamp(self):
        """Get the last successful sync timestamp from SyncHistory."""
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source='genius',
                sync_type='prospects',
                status='completed'
            ).order_by('-completed_at').first()
            
            if last_sync:
                return last_sync.completed_at
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not retrieve last sync timestamp: {e}"))
        
        return None
    
    def _determine_sync_strategy(self, options):
        """Determine sync strategy based on arguments with priority order."""
        # Priority: --since > --force-overwrite > --full > SyncHistory > full sync
        
        if options.get('since'):
            since_dt = self._parse_since_parameter(options['since'])
            return 'incremental', since_dt
        
        # Handle backward compatibility - --start-date is alias for --since  
        if options.get('start_date'):
            self.stdout.write(self.style.WARNING("--start-date is deprecated, use --since instead"))
            since_dt = self._parse_since_parameter(options['start_date'])
            return 'incremental', since_dt
            
        if options.get('force_overwrite') or options.get('full'):
            return 'full', None
            
        # Check SyncHistory for last sync
        last_sync = self._get_last_sync_timestamp()
        if last_sync:
            return 'incremental', last_sync
            
        # Default to full sync
        return 'full', None
    
    def _build_where_clause(self, sync_strategy, sync_timestamp, end_date):
        """Build WHERE clause for filtering records."""
        conditions = []
        
        if sync_strategy == 'incremental' and sync_timestamp:
            conditions.append(f"p.updated_at >= '{sync_timestamp.strftime('%Y-%m-%d %H:%M:%S')}'")
            
        if end_date:
            end_dt = self._parse_since_parameter(end_date)
            conditions.append(f"p.updated_at <= '{end_dt.strftime('%Y-%m-%d %H:%M:%S')}'")
            
        return " AND ".join(conditions)
    
    def _create_sync_record(self):
        """Create a new sync record."""
        return SyncHistory.objects.create(
            crm_source='genius',
            sync_type='prospects',
            status='running',
            started_at=timezone.now(),
            records_processed=0
        )
    
    def _complete_sync_record(self, sync_record, records_processed, status='completed'):
        """Complete the sync record."""
        sync_record.records_processed = records_processed
        sync_record.completed_at = timezone.now()
        sync_record.status = status
        sync_record.save()

    def _preload_divisions(self):
        """Preload divisions for lookup."""
        return {division.id: division for division in Genius_Division.objects.all()}
    
    def _preload_lookup_data(self, cursor):
        """Preload lookup data for better performance."""
        lookups = {
            'divisions': self._preload_divisions()
        }
        
        return lookups
    
    
    def _process_all_records(self, cursor, table_name, lookups, start_offset, start_page, 
                           sync_strategy, sync_timestamp, end_date, max_records):
        """Process all records in batches."""
        # Build WHERE clause for filtering
        where_clause = self._build_where_clause(sync_strategy, sync_timestamp, end_date)
        where_sql = f" WHERE {where_clause}" if where_clause else ""
        
        # Get total record count with filtering
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} AS p{where_sql}")
        total_records = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}' matching criteria: {total_records}"))
        
        if max_records and total_records > max_records:
            total_records = max_records
            self.stdout.write(self.style.SUCCESS(f"Limited to first {max_records:,} records"))
        
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
        processed_so_far = 0
        for offset in tqdm(range(start_offset, total_records, BATCH_SIZE), desc="Processing batches"):
            # Check max_records limit
            if max_records and processed_so_far >= max_records:
                break
                
            batch_size = min(BATCH_SIZE, total_records - offset)
            if max_records:
                batch_size = min(batch_size, max_records - processed_so_far)
                
            self._process_batch_at_offset(cursor, table_name, offset, lookups, where_sql, batch_size)
            processed_so_far += batch_size
            
    def _process_batch_at_offset(self, cursor, table_name, offset, lookups, where_sql="", batch_size=BATCH_SIZE):
        """Process a batch of records starting at the specified offset."""
        # Use JOIN to get HubSpot contact ID directly from third_party_source table
        cursor.execute(f"""
            SELECT p.id, p.division_id, p.user_id, p.first_name, p.last_name, p.alt_first_name, p.alt_last_name,
                   p.address1, p.address2, p.city, p.county, p.state, p.zip, p.year_built, p.phone1, p.phone2, 
                   p.email, p.notes, p.add_user_id, p.add_date, p.marketsharp_id, p.leap_customer_id, 
                   p.third_party_source_id, p.updated_at, tps.third_party_id AS hubspot_contact_id
            FROM {table_name} AS p
            LEFT JOIN third_party_source AS tps 
              ON tps.id = p.third_party_source_id
            LEFT JOIN third_party_source_type AS tpst 
              ON tpst.id = tps.third_party_source_type_id AND tpst.label = 'hubspot'
            {where_sql}
            ORDER BY p.id
            LIMIT {batch_size} OFFSET {offset}
        """)
        rows = cursor.fetchall()
        
        # Process the batch
        self._process_batch(rows, lookups)
    
    def _process_batch(self, rows, lookups):
        """Process a batch of prospect records."""
        to_create = []
        to_update = []
        existing_records = Genius_Prospect.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Validate row length first
                if len(row) != 25:  # Updated to 25 columns (added user_id and year_built fields)
                    self.stdout.write(self.style.WARNING(f"Row has {len(row)} columns, expected 25. Skipping record."))
                    continue
                
                # Extract fields from row with debugging
                try:
                    (
                        record_id, division_id, user_id, first_name, last_name, alt_first_name, alt_last_name,
                        address1, address2, city, county, state, zip, year_built, phone1, phone2, email, notes,
                        add_user_id, add_date, marketsharp_id, leap_customer_id, third_party_source_id, 
                        updated_at, hubspot_contact_id
                    ) = row
                except ValueError as e:
                    self.stdout.write(self.style.ERROR(f"Error unpacking row for record_id {row[0] if row else 'unknown'}: {e}"))
                    self.stdout.write(self.style.ERROR(f"Row data: {row}"))
                    continue

                # Get division
                division = lookups['divisions'].get(division_id)
                
                # Process datetime fields
                add_date = self._parse_datetime(add_date)
                updated_at = self._parse_datetime(updated_at)

                # The hubspot_contact_id is already resolved by the SQL JOIN
                # No additional lookup needed since the JOIN handles the mapping

                # Increment processed count
                self.processed_count += 1
                
                if self.debug:
                    if hubspot_contact_id:
                        self.stdout.write(f"📝 DEBUG: Processing record {record_id} - {first_name} {last_name} (Division: {division_id}, HubSpot: {hubspot_contact_id}, Third Party Source: {third_party_source_id})")
                    else:
                        self.stdout.write(f"📝 DEBUG: Processing record {record_id} - {first_name} {last_name} (Division: {division_id}, No HubSpot ID)")

                # Create or update record
                if record_id in existing_records:
                    record = self._update_record(existing_records[record_id], division, user_id, first_name, last_name,
                                           alt_first_name, alt_last_name, address1, address2, city, county,
                                           state, zip, year_built, phone1, phone2, email, notes, add_user_id, add_date,
                                           marketsharp_id, leap_customer_id, updated_at, hubspot_contact_id)
                    to_update.append(record)
                else:
                    record = self._create_record(record_id, division, user_id, first_name, last_name, alt_first_name,
                                           alt_last_name, address1, address2, city, county, state, zip, year_built,
                                           phone1, phone2, email, notes, add_user_id, add_date,
                                           marketsharp_id, leap_customer_id, updated_at, hubspot_contact_id)
                    to_create.append(record)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing record ID {row[0] if row else 'unknown'}: {e}"))
                self.stdout.write(self.style.ERROR(f"Row data: {row}"))

        # Save records to database
        if not self.dry_run:
            self._save_records(to_create, to_update)
        else:
            # In dry run mode, just show what would be saved
            if to_create:
                self.stdout.write(self.style.WARNING(f"DRY RUN: Would create {len(to_create)} new prospect records"))
                if self.debug:
                    for record in to_create[:5]:  # Show first 5 records in debug mode
                        self.stdout.write(f"  🆕 Would create: {record.first_name} {record.last_name} (ID: {record.id})")
                    if len(to_create) > 5:
                        self.stdout.write(f"  ... and {len(to_create) - 5} more records")
            
            if to_update:
                self.stdout.write(self.style.WARNING(f"DRY RUN: Would update {len(to_update)} existing prospect records"))
                if self.debug:
                    for record in to_update[:5]:  # Show first 5 records in debug mode
                        self.stdout.write(f"  ♻️  Would update: {record.first_name} {record.last_name} (ID: {record.id})")
                    if len(to_update) > 5:
                        self.stdout.write(f"  ... and {len(to_update) - 5} more records")
    
    def _update_record(self, record, division, user_id, first_name, last_name, alt_first_name, alt_last_name,
                     address1, address2, city, county, state, zip, year_built, phone1, phone2, email, notes,
                     add_user_id, add_date, marketsharp_id, leap_customer_id, updated_at, hubspot_contact_id):
        """Update an existing prospect record."""
        record.division = division
        record.user_id = user_id
        record.first_name = first_name
        record.last_name = last_name
        record.alt_first_name = alt_first_name
        record.alt_last_name = alt_last_name
        record.address1 = address1
        record.address2 = address2
        record.city = city
        record.county = county
        record.state = state
        record.zip = zip
        record.year_built = year_built
        record.phone1 = phone1
        record.phone2 = phone2
        record.email = email
        record.notes = notes
        record.add_user_id = add_user_id
        record.add_date = add_date
        record.marketsharp_id = marketsharp_id
        record.leap_customer_id = leap_customer_id
        record.updated_at = updated_at
        record.hubspot_contact_id = hubspot_contact_id
        return record
    
    def _create_record(self, record_id, division, user_id, first_name, last_name, alt_first_name, alt_last_name,
                     address1, address2, city, county, state, zip, year_built, phone1, phone2, email, notes,
                     add_user_id, add_date, marketsharp_id, leap_customer_id, updated_at, hubspot_contact_id):
        """Create a new prospect record."""
        return Genius_Prospect(
            id=record_id,
            division=division,
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            alt_first_name=alt_first_name,
            alt_last_name=alt_last_name,
            address1=address1,
            address2=address2,
            city=city,
            county=county,
            state=state,
            zip=zip,
            year_built=year_built,
            phone1=phone1,
            phone2=phone2,
            email=email,
            notes=notes,
            add_user_id=add_user_id,
            add_date=add_date,
            marketsharp_id=marketsharp_id,
            leap_customer_id=leap_customer_id,
            updated_at=updated_at,
            hubspot_contact_id=hubspot_contact_id
        )
    
    def _save_records(self, to_create, to_update):
        """Save records to database with error handling."""
        try:
            if to_create:
                Genius_Prospect.objects.bulk_create(to_create, batch_size=BATCH_SIZE, ignore_conflicts=True)
            
            if to_update:
                Genius_Prospect.objects.bulk_update(
                    to_update,
                    [
                        'division', 'user_id', 'first_name', 'last_name', 'alt_first_name', 'alt_last_name',
                        'address1', 'address2', 'city', 'county', 'state', 'zip', 'year_built', 'phone1', 'phone2',
                        'email', 'notes', 'add_user_id', 'add_date', 'marketsharp_id', 'leap_customer_id',
                        'updated_at', 'hubspot_contact_id'
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
                if not record.division:
                    self.stdout.write(self.style.WARNING(f"Skipping record {record.id}: missing division"))
                    continue
                    
                record.save()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving record {record.id}: {e}"))
    
    def _safe_int_convert(self, value, default=None, field_name="unknown"):
        """Safely convert value to integer with validation."""
        if value is None:
            return default
        
        try:
            int_val = int(value)
            return int_val
        except (ValueError, TypeError):
            self.stdout.write(self.style.WARNING(f"Invalid integer value for {field_name}: {value}, using default {default}"))
            return default

    def _safe_string_convert(self, value, default=None):
        """Safely convert value to string."""
        if value is None:
            return default
        
        try:
            return str(value)
        except (ValueError, TypeError):
            self.stdout.write(self.style.WARNING(f"Invalid string value: {value}, using default {default}"))
            return default
    
    def _parse_datetime(self, value):
        """Helper function to safely parse and make datetime timezone-aware."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return timezone.make_aware(value, dt_timezone.utc) if timezone.is_naive(value) else value
        
        return value

