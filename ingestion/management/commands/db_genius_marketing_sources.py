import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import MarketingSource
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
                cursor.execute(f"""
                    SELECT id, type_id, label, description, start_date, end_date, add_user_id, add_date,
                           is_active, is_allow_lead_modification
                    FROM {table_name}
                    LIMIT {BATCH_SIZE} OFFSET {offset}
                """)
                rows = cursor.fetchall()
                self._process_batch(rows)

            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:  # Ensure the connection is closed only if it was established
                cursor.close()
                connection.close()

    def _process_batch(self, rows):
        """Process a single batch of records."""
        to_create = []
        to_update = []
        existing_records = MarketingSource.objects.in_bulk([row[0] for row in rows])  # Assuming the first column is the primary key

        for row in rows:
            (
                record_id, type_id, label, description, start_date, end_date, add_user_id, add_date,
                is_active, is_allow_lead_modification
            ) = row

            if add_date:
                add_date = timezone.make_aware(add_date, dt_timezone.utc)  # Use datetime.timezone.utc

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
                to_update.append(record_instance)
            else:
                to_create.append(MarketingSource(
                    id=record_id,
                    type_id=type_id,
                    label=label,
                    description=description,
                    start_date=start_date,
                    end_date=end_date,
                    add_user_id=add_user_id,
                    add_date=add_date,
                    is_active=is_active,
                    is_allow_lead_modification=is_allow_lead_modification
                ))

        # Bulk create and update
        if to_create:
            MarketingSource.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
        if to_update:
            MarketingSource.objects.bulk_update(
                to_update,
                [
                    'type_id', 'label', 'description', 'start_date', 'end_date', 'add_user_id',
                    'add_date', 'is_active', 'is_allow_lead_modification'
                ],
                batch_size=BATCH_SIZE
            )
