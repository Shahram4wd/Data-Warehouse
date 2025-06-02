import os
import mysql.connector
from django.core.management.base import BaseCommand
from ingestion.models import AppointmentOutcome
from tqdm import tqdm

BATCH_SIZE = 500

class Command(BaseCommand):
    help = "Download appointment outcomes directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="appointment_outcome",
            help="The name of the table to download data from. Defaults to 'appointment_outcome'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]

        # Database connection details from environment variables
        db_host = os.getenv("GENIUS_DB_HOST")
        db_name = os.getenv("GENIUS_DB_NAME")
        db_user = os.getenv("GENIUS_DB_USER")
        db_password = os.getenv("GENIUS_DB_PASSWORD")
        db_port = os.getenv("GENIUS_DB_PORT", 3306)  # Default to 3306 if not set

        if not all([db_host, db_name, db_user, db_password]):
            self.stdout.write(self.style.ERROR("Database connection details are missing in environment variables."))
            return

        connection = None  # Initialize the connection variable
        try:
            # Connect to the external MySQL database
            connection = mysql.connector.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=db_port  # Use the correct port
            )
            cursor = connection.cursor()

            # Fetch data from the specified table
            self.stdout.write(self.style.SUCCESS(f"Fetching data from table '{table_name}'..."))
            cursor.execute(f"SELECT id, type_id, label, is_active FROM {table_name}")
            rows = cursor.fetchall()

            # Process rows
            to_create = []
            to_update = []
            existing_records = AppointmentOutcome.objects.in_bulk([row[0] for row in rows])  # Assuming the first column is the primary key

            for row in tqdm(rows):
                record_id, type_id, label, is_active = row
                if record_id in existing_records:
                    record_instance = existing_records[record_id]
                    record_instance.type_id = type_id
                    record_instance.label = label
                    record_instance.is_active = bool(is_active)
                    to_update.append(record_instance)
                else:
                    to_create.append(AppointmentOutcome(
                        id=record_id,
                        type_id=type_id,
                        label=label,
                        is_active=bool(is_active)
                    ))

                if len(to_update) >= BATCH_SIZE or len(to_create) >= BATCH_SIZE:
                    self._process_batches(to_create, to_update)

            # Final batch processing
            self._process_batches(to_create, to_update)

            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:  # Ensure the connection is closed only if it was established
                cursor.close()
                connection.close()

    def _process_batches(self, to_create, to_update):
        """Helper method to process batches of records."""
        if to_create:
            AppointmentOutcome.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
            to_create.clear()
        if to_update:
            AppointmentOutcome.objects.bulk_update(to_update, ['type_id', 'label', 'is_active'], batch_size=BATCH_SIZE)
            to_update.clear()
