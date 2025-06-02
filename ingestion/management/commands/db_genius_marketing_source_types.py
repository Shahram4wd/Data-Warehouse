import os
from django.core.management.base import BaseCommand
from ingestion.models import MarketingSourceType
from ingestion.utils import get_mysql_connection
from tqdm import tqdm

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))  # Default to 500 if not set

class Command(BaseCommand):
    help = "Download marketing source types directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="marketing_source_type",
            help="The name of the table to download data from. Defaults to 'marketing_source_type'."
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
                    SELECT id, label, description, is_active, list_order
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
        existing_records = MarketingSourceType.objects.in_bulk([row[0] for row in rows])  # Assuming the first column is the primary key

        for row in rows:
            (
                record_id, label, description, is_active, list_order
            ) = row

            if record_id in existing_records:
                record_instance = existing_records[record_id]
                record_instance.label = label
                record_instance.description = description
                record_instance.is_active = is_active
                record_instance.list_order = list_order
                to_update.append(record_instance)
            else:
                to_create.append(MarketingSourceType(
                    id=record_id,
                    label=label,
                    description=description,
                    is_active=is_active,
                    list_order=list_order
                ))

        # Bulk create and update
        if to_create:
            MarketingSourceType.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
        if to_update:
            MarketingSourceType.objects.bulk_update(
                to_update,
                ['label', 'description', 'is_active', 'list_order'],
                batch_size=BATCH_SIZE
            )
