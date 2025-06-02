import os
import psycopg2
from django.core.management.base import BaseCommand
from ingestion.utils import process_batches
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
        db_password = os.getenv("DB_PASSWORD")

        if not all([db_host, db_name, db_user, db_password]):
            self.stdout.write(self.style.ERROR("Database connection details are missing in environment variables."))
            return

        try:
            # Connect to the external database
            connection = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password
            )
            cursor = connection.cursor()

            # Fetch data from the specified table
            self.stdout.write(self.style.SUCCESS(f"Fetching data from table '{table_name}'..."))
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            # Get column names
            column_names = [desc[0] for desc in cursor.description]

            # Process rows
            to_create = []
            to_update = []
            existing_records = AppointmentOutcome.objects.in_bulk([row[0] for row in rows])  # Assuming the first column is the primary key

            for row in tqdm(rows):
                record_data = dict(zip(column_names, row))
                record_id = record_data["id"]

                if record_id in existing_records:
                    record_instance = existing_records[record_id]
                    for attr, val in record_data.items():
                        setattr(record_instance, attr, val)
                    to_update.append(record_instance)
                else:
                    to_create.append(AppointmentOutcome(**record_data))

                if len(to_update) >= BATCH_SIZE or len(to_create) >= BATCH_SIZE:
                    process_batches(to_create, to_update, AppointmentOutcome, column_names, BATCH_SIZE)

            # Final batch processing
            process_batches(to_create, to_update, AppointmentOutcome, column_names, BATCH_SIZE)

            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
