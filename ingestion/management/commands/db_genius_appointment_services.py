import os
from django.core.management.base import BaseCommand
from ingestion.models import Genius_AppointmentService, Genius_Appointment, Genius_Service
from ingestion.utils import get_mysql_connection
from tqdm import tqdm

BATCH_SIZE = 500

class Command(BaseCommand):
    help = "Download appointment services directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="appointment_to_service",
            help="The name of the table to download data from. Defaults to 'appointment_service'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]

        connection = None  # Initialize the connection variable
        try:
            # Use the utility function to get the database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()

            # Fetch data from the specified table
            self.stdout.write(self.style.SUCCESS(f"Fetching data from table '{table_name}'..."))
            cursor.execute(f"SELECT appointment_id, service_id FROM {table_name}")
            rows = cursor.fetchall()

            # Process rows
            to_create = []
            to_update = []
            
            # Get existing records based on the unique combination of appointment_id and service_id
            existing_records = {}
            existing_appointment_services = Genius_AppointmentService.objects.select_related('appointment', 'service').all()
            for record in existing_appointment_services:
                key = (record.appointment_id, record.service_id)
                existing_records[key] = record

            # Get all appointment and service objects for validation
            appointment_ids = set(row[0] for row in rows)
            service_ids = set(row[1] for row in rows)
            
            existing_appointments = set(Genius_Appointment.objects.filter(id__in=appointment_ids).values_list('id', flat=True))
            existing_services = set(Genius_Service.objects.filter(id__in=service_ids).values_list('id', flat=True))

            skipped_count = 0
            processed_count = 0

            for row in tqdm(rows):
                appointment_id, service_id = row
                
                # Skip if referenced appointment or service doesn't exist
                if appointment_id not in existing_appointments:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f"Skipping: Appointment {appointment_id} not found"))
                    continue
                    
                if service_id not in existing_services:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f"Skipping: Service {service_id} not found"))
                    continue

                key = (appointment_id, service_id)
                processed_count += 1
                
                if key in existing_records:
                    # Record exists, but since it's just a junction table with no additional fields to update,
                    # we don't need to do anything unless you want to track updates
                    pass
                else:
                    # Create new appointment service record
                    to_create.append(Genius_AppointmentService(
                        appointment_id=appointment_id,
                        service_id=service_id
                    ))

                if len(to_create) >= BATCH_SIZE:
                    self._process_batches(to_create, to_update)

            # Final batch processing
            self._process_batches(to_create, to_update)

            self.stdout.write(self.style.SUCCESS(
                f"Data from table '{table_name}' successfully downloaded and updated. "
                f"Processed: {processed_count}, Skipped: {skipped_count}, Created: {len(to_create)}"
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:  # Ensure the connection is closed only if it was established
                cursor.close()
                connection.close()

    def _process_batches(self, to_create, to_update):
        """Helper method to process batches of records."""
        if to_create:
            try:
                Genius_AppointmentService.objects.bulk_create(to_create, batch_size=BATCH_SIZE, ignore_conflicts=True)
                created_count = len(to_create)
                self.stdout.write(self.style.SUCCESS(f"Created {created_count} appointment service records"))
                to_create.clear()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating appointment service records: {e}"))
                to_create.clear()
        
        if to_update:
            # Since this is a junction table with only foreign keys, there are no fields to update
            # But we keep this structure for consistency with the base command
            to_update.clear()
