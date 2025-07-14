import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_Prospect, Genius_Division
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
    
    def handle(self, *args, **options):
        table_name = options["table"]
        start_offset = options["start_offset"]
        start_page = options["page"]
        dry_run = options.get("dry_run", False)
        debug = options.get("debug", False)
        connection = None
        
        # Initialize counters
        self.processed_count = 0
        self.dry_run = dry_run
        self.debug = debug
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes will be made"))
        if debug:
            self.stdout.write(self.style.SUCCESS("🐛 DEBUG MODE - Verbose logging enabled"))

        try:
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data
            lookups = self._preload_lookup_data(cursor)
            
            # Process records in batches
            self._process_all_records(cursor, table_name, lookups, start_offset, start_page)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
            # Print summary
            if dry_run:
                self.stdout.write(self.style.WARNING(f"DRY RUN Summary: {self.processed_count} records would be processed (no database changes made)."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Summary: {self.processed_count} records processed successfully."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _preload_divisions(self):
        """Preload divisions for lookup."""
        return {division.id: division for division in Genius_Division.objects.all()}
    
    def _preload_lookup_data(self, cursor):
        """Preload lookup data for better performance."""
        lookups = {
            'divisions': self._preload_divisions()
        }
        
        return lookups
    
    
    def _process_all_records(self, cursor, table_name, lookups, start_offset, start_page):
        """Process all records in batches."""
        # Get total record count
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
            self._process_batch_at_offset(cursor, table_name, offset, lookups)
    def _process_batch_at_offset(self, cursor, table_name, offset, lookups):
        """Process a batch of records starting at the specified offset."""
        # Use JOIN to get HubSpot contact ID directly from third_party_source table
        cursor.execute(f"""
            SELECT p.id, p.division_id, p.first_name, p.last_name, p.alt_first_name, p.alt_last_name,
                   p.address1, p.address2, p.city, p.county, p.state, p.zip, p.phone1, p.phone2, 
                   p.email, p.notes, p.add_user_id, p.add_date, p.marketsharp_id, p.leap_customer_id, 
                   p.third_party_source_id, tps.third_party_id AS hubspot_contact_id
            FROM {table_name} AS p
            LEFT JOIN third_party_source AS tps 
              ON tps.id = p.third_party_source_id
            LEFT JOIN third_party_source_type AS tpst 
              ON tpst.id = tps.third_party_source_type_id AND tpst.label = 'hubspot'
            LIMIT {BATCH_SIZE} OFFSET {offset}
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
                if len(row) != 22:  # Updated to 22 columns (added third_party_source_id and hubspot_contact_id)
                    self.stdout.write(self.style.WARNING(f"Row has {len(row)} columns, expected 22. Skipping record."))
                    continue
                
                # Extract fields from row with debugging
                try:
                    (
                        record_id, division_id, first_name, last_name, alt_first_name, alt_last_name,
                        address1, address2, city, county, state, zip, phone1, phone2, email, notes,
                        add_user_id, add_date, marketsharp_id, leap_customer_id, third_party_source_id, 
                        hubspot_contact_id
                    ) = row
                except ValueError as e:
                    self.stdout.write(self.style.ERROR(f"Error unpacking row for record_id {row[0] if row else 'unknown'}: {e}"))
                    self.stdout.write(self.style.ERROR(f"Row data: {row}"))
                    continue

                # Get division
                division = lookups['divisions'].get(division_id)
                
                # Process datetime fields
                add_date = self._parse_datetime(add_date)

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
                    record = self._update_record(existing_records[record_id], division, first_name, last_name,
                                           alt_first_name, alt_last_name, address1, address2, city, county,
                                           state, zip, phone1, phone2, email, notes, add_user_id, add_date,
                                           marketsharp_id, leap_customer_id, hubspot_contact_id)
                    to_update.append(record)
                else:
                    record = self._create_record(record_id, division, first_name, last_name, alt_first_name,
                                           alt_last_name, address1, address2, city, county, state, zip,
                                           phone1, phone2, email, notes, add_user_id, add_date,
                                           marketsharp_id, leap_customer_id, hubspot_contact_id)
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
    
    def _update_record(self, record, division, first_name, last_name, alt_first_name, alt_last_name,
                     address1, address2, city, county, state, zip, phone1, phone2, email, notes,
                     add_user_id, add_date, marketsharp_id, leap_customer_id, hubspot_contact_id):
        """Update an existing prospect record."""
        record.division = division
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
        record.phone1 = phone1
        record.phone2 = phone2
        record.email = email
        record.notes = notes
        record.add_user_id = add_user_id
        record.add_date = add_date
        record.marketsharp_id = marketsharp_id
        record.leap_customer_id = leap_customer_id
        record.hubspot_contact_id = hubspot_contact_id
        return record
    
    def _create_record(self, record_id, division, first_name, last_name, alt_first_name, alt_last_name,
                     address1, address2, city, county, state, zip, phone1, phone2, email, notes,
                     add_user_id, add_date, marketsharp_id, leap_customer_id, hubspot_contact_id):
        """Create a new prospect record."""
        return Genius_Prospect(
            id=record_id,
            division=division,
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
            phone1=phone1,
            phone2=phone2,
            email=email,
            notes=notes,
            add_user_id=add_user_id,
            add_date=add_date,
            marketsharp_id=marketsharp_id,
            leap_customer_id=leap_customer_id,
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
                        'division', 'first_name', 'last_name', 'alt_first_name', 'alt_last_name',
                        'address1', 'address2', 'city', 'county', 'state', 'zip', 'phone1', 'phone2',
                        'email', 'notes', 'add_user_id', 'add_date', 'marketsharp_id', 'leap_customer_id',
                        'hubspot_contact_id'
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

