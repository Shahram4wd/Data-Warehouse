import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models.genius import Genius_MarketSharpMarketingSourceMap
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download MarketSharp source maps directly from the database and update the local database."

    def handle(self, *args, **options):
        table_name = "marketsharp_marketing_source_map"
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

            # Process records in batches
            for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
                cursor.execute(f"""
                    SELECT marketsharp_id, marketing_source_id
                    FROM {table_name}
                    LIMIT {BATCH_SIZE} OFFSET {offset}
                """)
                rows = cursor.fetchall()
                self._process_batch(rows)

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

    def _process_batch(self, rows):
        """Process a batch of MarketSharp source map records."""
        to_create = []
        to_update = []
        existing_records = Genius_MarketSharpMarketingSourceMap.objects.in_bulk([row[0] for row in rows], field_name='marketsharp_id')

        for row in rows:
            try:
                # Validate row length first
                if len(row) != 2:  # Expected number of columns
                    self.stdout.write(self.style.WARNING(f"Row has {len(row)} columns, expected 2. Skipping record."))
                    continue

                # Extract fields from row with debugging
                try:
                    marketsharp_id, marketing_source_id = row
                except ValueError as e:
                    self.stdout.write(self.style.ERROR(f"Error unpacking row for marketsharp_id {row[0] if row else 'unknown'}: {e}"))
                    self.stdout.write(self.style.ERROR(f"Row data: {row}"))
                    continue

                # Increment processed count
                self.processed_count += 1

                # Process fields with validation
                processed_data = {
                    'marketsharp_id': self._safe_string_convert(marketsharp_id),
                    'marketing_source_id': self._safe_int_convert(marketing_source_id, -1, field_name="marketing_source_id", original_row=row)
                }

                # Create or update the record
                if marketsharp_id in existing_records:
                    record = existing_records[marketsharp_id]
                    self._update_record(record, processed_data)
                    to_update.append(record)
                else:
                    record = self._create_record(processed_data)
                    to_create.append(record)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing record with marketsharp_id {row[0] if row else 'unknown'}: {e}"))

        # Save records to database
        self._save_records(to_create, to_update)

    def _update_record(self, record, processed_data):
        """Update an existing record with new values."""
        record.marketsharp_id = processed_data['marketsharp_id']
        record.marketing_source_id = processed_data['marketing_source_id']
        return record

    def _create_record(self, processed_data):
        """Create a new MarketSharp source map record."""
        return Genius_MarketSharpMarketingSourceMap(
            marketsharp_id=processed_data['marketsharp_id'],
            marketing_source_id=processed_data['marketing_source_id']
        )

    def _save_records(self, to_create, to_update):
        """Save records to database with error handling."""
        try:
            if to_create:
                Genius_MarketSharpMarketingSourceMap.objects.bulk_create(to_create, batch_size=BATCH_SIZE, ignore_conflicts=True)
                self.stdout.write(f"Created {len(to_create)} records")

            if to_update:
                Genius_MarketSharpMarketingSourceMap.objects.bulk_update(
                    to_update,
                    ['marketsharp_id', 'marketing_source_id'],
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

    def _safe_int_convert(self, value, default=None, field_name=None, original_row=None):
        """Safely convert value to integer."""
        if value is None:
            return default

        try:
            return int(value)
        except (ValueError, TypeError):
            self.stdout.write(self.style.WARNING(
                f"Invalid integer value for field '{field_name}': {value}, using default {default}. Row: {original_row}"
            ))
            self.corrupted_count += 1
            return default
