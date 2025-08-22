import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models.genius import Genius_MarketSharpSource
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download MarketSharp sources directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="marketsharp_source",
            help="The name of the table to download data from. Defaults to 'marketsharp_source'."
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
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
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
                # Try to get timestamps from source, fall back to 4-field query if they don't exist
                try:
                    cursor.execute(f"""
                        SELECT id, marketsharp_id, source_name, inactive, created_at, updated_at
                        FROM {table_name}
                        LIMIT {BATCH_SIZE} OFFSET {offset}
                    """)
                    rows = cursor.fetchall()
                    has_timestamps = True
                except Exception as e:
                    # Fallback to original query without timestamps
                    self.stdout.write(self.style.WARNING(f"Source table doesn't have timestamp fields, using fallback query: {e}"))
                    cursor.execute(f"""
                        SELECT id, marketsharp_id, source_name, inactive
                        FROM {table_name}
                        LIMIT {BATCH_SIZE} OFFSET {offset}
                    """)
                    rows = cursor.fetchall()
                    has_timestamps = False
                
                self._process_batch(rows, has_timestamps)
                
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
    
    def _process_batch(self, rows, has_timestamps=False):
        """Process a batch of MarketSharp source records."""
        to_create = []
        to_update = []
        existing_records = Genius_MarketSharpSource.objects.in_bulk([row[0] for row in rows])
        
        expected_columns = 6 if has_timestamps else 4

        for row in rows:
            try:
                # Validate row length first
                if len(row) != expected_columns:
                    self.stdout.write(self.style.WARNING(f"Row has {len(row)} columns, expected {expected_columns}. Skipping record."))
                    continue
                
                # Extract fields from row with debugging
                try:
                    if has_timestamps:
                        record_id, marketsharp_id, source_name, inactive, created_at, updated_at = row
                    else:
                        record_id, marketsharp_id, source_name, inactive = row
                        created_at = updated_at = None
                except ValueError as e:
                    self.stdout.write(self.style.ERROR(f"Error unpacking row for record_id {row[0] if row else 'unknown'}: {e}"))
                    self.stdout.write(self.style.ERROR(f"Row data: {row}"))
                    continue

                # Increment processed count
                self.processed_count += 1
                
                # Process fields with validation
                processed_data = {
                    'marketsharp_id': self._safe_string_convert(marketsharp_id),
                    'source_name': self._safe_string_convert(source_name),
                    'inactive': self._safe_int_convert(inactive, 0, field_name="inactive", original_row=row),
                    'created_at': self._safe_datetime_convert(created_at),
                    'updated_at': self._safe_datetime_convert(updated_at)
                }
                
                # Create or update the record
                if record_id in existing_records:
                    record = existing_records[record_id]
                    self._update_record(record, processed_data)
                    to_update.append(record)
                else:
                    record = self._create_record(record_id, processed_data)
                    to_create.append(record)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing record ID {row[0] if row else 'unknown'}: {e}"))

        # Save records to database
        self._save_records(to_create, to_update)

    def _safe_string_convert(self, value, default=None):
        """Safely convert value to string."""
        if value is None:
            return default
        
        try:
            return str(value).strip() if str(value).strip() else default
        except (ValueError, TypeError):
            self.stdout.write(self.style.WARNING(f"Invalid string value: {value}, using default {default}"))
            self.corrupted_count += 1
            return default

    def _safe_int_convert(self, value, default=None, field_name="unknown", original_row=None):
        """Safely convert value to integer with range validation."""
        if value is None:
            return default
        
        try:
            int_val = int(value)
            
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

    def _safe_datetime_convert(self, value, default=None):
        """Safely convert value to timezone-aware datetime."""
        if value is None:
            return timezone.now() if default is None else default
        
        try:
            from datetime import datetime
            
            # If it's already a datetime object
            if hasattr(value, 'year'):
                # Check if it's naive (no timezone info) and make it aware
                if timezone.is_naive(value):
                    return timezone.make_aware(value)
                return value
            
            # Try to convert string to datetime
            if isinstance(value, str):
                try:
                    # Parse ISO format datetime
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    if timezone.is_naive(dt):
                        return timezone.make_aware(dt)
                    return dt
                except ValueError:
                    pass
            
            # If conversion fails, return current time
            return timezone.now()
        except (ValueError, TypeError, AttributeError):
            self.stdout.write(self.style.WARNING(f"Invalid datetime value: {value}, using current time"))
            self.corrupted_count += 1
            return timezone.now()

    def _update_record(self, record, processed_data):
        """Update an existing record with new values."""
        record.marketsharp_id = processed_data['marketsharp_id']
        record.source_name = processed_data['source_name']
        record.inactive = processed_data['inactive']
        record.created_at = processed_data['created_at']
        record.updated_at = processed_data['updated_at']

        return record
    
    def _create_record(self, record_id, processed_data):
        """Create a new MarketSharp source record."""
        return Genius_MarketSharpSource(
            id=record_id,
            marketsharp_id=processed_data['marketsharp_id'],
            source_name=processed_data['source_name'],
            inactive=processed_data['inactive'],
            created_at=processed_data['created_at'],
            updated_at=processed_data['updated_at'],
        )
    
    def _save_records(self, to_create, to_update):
        """Save records to database with error handling."""
        try:
            if to_create:
                Genius_MarketSharpSource.objects.bulk_create(to_create, batch_size=BATCH_SIZE, ignore_conflicts=True)
                self.stdout.write(f"Created {len(to_create)} records")
            
            if to_update:
                Genius_MarketSharpSource.objects.bulk_update(
                    to_update,
                    ['marketsharp_id', 'source_name', 'inactive', 'updated_at'],
                    batch_size=BATCH_SIZE
                )
                self.stdout.write(f"Updated {len(to_update)} records")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during bulk operations: {e}"))
            self._fallback_individual_saves(to_create + to_update)
    
    def _fallback_individual_saves(self, records):
        """Fallback to individual saves when bulk operations fail."""
        for record in records:
            try:
                record.save()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving record {record.id}: {e}"))
