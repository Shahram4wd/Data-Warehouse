import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_MarketingSource
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone  # Import Python's datetime timezone

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))  # Default to 500 if not set

class Command(BaseCommand):
    help = "Download marketing sources directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="marketing_source",
            help="The name of the table to download data from. Defaults to 'marketing_source'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]

        connection = None  # Initialize the connection variable
        try:
            # Use the utility function to get the database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()

            # Fetch total record count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_records = cursor.fetchone()[0]
            self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))

            # Process records in batches
            for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
                # Try to get updated_at from source, fall back without it if it doesn't exist
                try:
                    cursor.execute(f"""
                        SELECT id, type_id, label, description, start_date, end_date, add_user_id, add_date,
                               is_active, is_allow_lead_modification, updated_at
                        FROM {table_name}
                        LIMIT {BATCH_SIZE} OFFSET {offset}
                    """)
                    rows = cursor.fetchall()
                    has_updated_at = True
                except Exception as e:
                    # Fallback to original query without updated_at
                    self.stdout.write(self.style.WARNING(f"Source table doesn't have updated_at field, using fallback query: {e}"))
                    cursor.execute(f"""
                        SELECT id, type_id, label, description, start_date, end_date, add_user_id, add_date,
                               is_active, is_allow_lead_modification
                        FROM {table_name}
                        LIMIT {BATCH_SIZE} OFFSET {offset}
                    """)
                    rows = cursor.fetchall()
                    has_updated_at = False
                
                self._process_batch(rows, has_updated_at)

            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:  # Ensure the connection is closed only if it was established
                cursor.close()
                connection.close()

    def _process_batch(self, rows, has_updated_at=False):
        """Process a single batch of records."""
        to_create = []
        to_update = []
        existing_records = Genius_MarketingSource.objects.in_bulk([row[0] for row in rows])  # Assuming the first column is the primary key

        for row in rows:
            if has_updated_at:
                (
                    record_id, type_id, label, description, start_date, end_date, add_user_id, add_date,
                    is_active, is_allow_lead_modification, updated_at
                ) = row
            else:
                (
                    record_id, type_id, label, description, start_date, end_date, add_user_id, add_date,
                    is_active, is_allow_lead_modification
                ) = row
                updated_at = None

            # Convert datetime fields to timezone-aware
            if add_date:
                add_date = self._safe_datetime_convert(add_date)
            
            # Handle updated_at field
            updated_at = self._safe_datetime_convert(updated_at)

            if record_id in existing_records:
                record_instance = existing_records[record_id]
                record_instance.type_id = type_id
                record_instance.label = label
                record_instance.description = description
                record_instance.start_date = start_date
                record_instance.end_date = end_date
                record_instance.add_user_id = add_user_id
                record_instance.add_date = add_date
                record_instance.is_active = is_active
                record_instance.is_allow_lead_modification = is_allow_lead_modification
                record_instance.updated_at = updated_at
                to_update.append(record_instance)
            else:
                to_create.append(Genius_MarketingSource(
                    id=record_id,
                    type_id=type_id,
                    label=label,
                    description=description,
                    start_date=start_date,
                    end_date=end_date,
                    add_user_id=add_user_id,
                    add_date=add_date,
                    is_active=is_active,
                    is_allow_lead_modification=is_allow_lead_modification,
                    updated_at=updated_at
                ))

        # Bulk create and update
        if to_create:
            Genius_MarketingSource.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
        if to_update:
            Genius_MarketingSource.objects.bulk_update(
                to_update,
                [
                    'type_id', 'label', 'description', 'start_date', 'end_date', 'add_user_id',
                    'add_date', 'is_active', 'is_allow_lead_modification', 'updated_at'
                ],
                batch_size=BATCH_SIZE
            )

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
            return timezone.now()
