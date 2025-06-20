import os
from django.core.management.base import BaseCommand
from ingestion.models import Genius_Quote, Genius_Prospect, Genius_Appointment, Genius_Service
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from decimal import Decimal
from datetime import datetime

BATCH_SIZE = 500

class Command(BaseCommand):
    help = "Download quotes directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="quote",
            help="The name of the table to download data from. Defaults to 'quote'."
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
            cursor.execute(f"""
                SELECT id, prospect_id, appointment_id, job_id, client_cid, service_id, 
                       label, description, amount, expire_date, status_id, 
                       contract_file_id, estimate_file_id, add_user_id, add_date 
                FROM {table_name}
            """)
            rows = cursor.fetchall()

            # Process rows
            to_create = []
            to_update = []
            existing_records = Genius_Quote.objects.in_bulk([row[0] for row in rows])

            # Get all referenced objects for validation
            prospect_ids = set(row[1] for row in rows if row[1])
            appointment_ids = set(row[2] for row in rows if row[2])
            service_ids = set(row[5] for row in rows if row[5])
            
            existing_prospects = set(Genius_Prospect.objects.filter(id__in=prospect_ids).values_list('id', flat=True))
            existing_appointments = set(Genius_Appointment.objects.filter(id__in=appointment_ids).values_list('id', flat=True))
            existing_services = set(Genius_Service.objects.filter(id__in=service_ids).values_list('id', flat=True))

            skipped_count = 0
            processed_count = 0

            for row in tqdm(rows):
                (quote_id, prospect_id, appointment_id, job_id, client_cid, service_id, 
                 label, description, amount, expire_date, status_id, 
                 contract_file_id, estimate_file_id, add_user_id, add_date) = row
                
                # Skip if required foreign keys don't exist
                if prospect_id and prospect_id not in existing_prospects:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f"Skipping quote {quote_id}: Prospect {prospect_id} not found"))
                    continue
                    
                if appointment_id and appointment_id not in existing_appointments:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f"Skipping quote {quote_id}: Appointment {appointment_id} not found"))
                    continue
                    
                if service_id and service_id not in existing_services:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f"Skipping quote {quote_id}: Service {service_id} not found"))
                    continue

                processed_count += 1
                
                # Convert amount to Decimal
                amount_decimal = Decimal(str(amount)) if amount is not None else Decimal('0.00')
                
                if quote_id in existing_records:
                    # Update existing quote
                    record_instance = existing_records[quote_id]
                    record_instance.prospect_id = prospect_id
                    record_instance.appointment_id = appointment_id
                    record_instance.job_id = job_id
                    record_instance.client_cid = client_cid
                    record_instance.service_id = service_id
                    record_instance.label = label
                    record_instance.description = description
                    record_instance.amount = amount_decimal
                    record_instance.expire_date = expire_date
                    record_instance.status_id = status_id or 1
                    record_instance.contract_file_id = contract_file_id
                    record_instance.estimate_file_id = estimate_file_id
                    record_instance.add_user_id = add_user_id
                    # Note: add_date is auto_now_add=True, so we don't update it
                    to_update.append(record_instance)
                else:
                    # Create new quote
                    to_create.append(Genius_Quote(
                        id=quote_id,
                        prospect_id=prospect_id,
                        appointment_id=appointment_id,
                        job_id=job_id,
                        client_cid=client_cid,
                        service_id=service_id,
                        label=label,
                        description=description,
                        amount=amount_decimal,
                        expire_date=expire_date,
                        status_id=status_id or 1,
                        contract_file_id=contract_file_id,
                        estimate_file_id=estimate_file_id,
                        add_user_id=add_user_id
                        # add_date will be set automatically
                    ))

                if len(to_update) >= BATCH_SIZE or len(to_create) >= BATCH_SIZE:
                    self._process_batches(to_create, to_update)

            # Final batch processing
            self._process_batches(to_create, to_update)

            self.stdout.write(self.style.SUCCESS(
                f"Data from table '{table_name}' successfully downloaded and updated. "
                f"Processed: {processed_count}, Skipped: {skipped_count}"
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
                Genius_Quote.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
                created_count = len(to_create)
                self.stdout.write(self.style.SUCCESS(f"Created {created_count} quote records"))
                to_create.clear()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating quote records: {e}"))
                to_create.clear()
        
        if to_update:
            try:
                Genius_Quote.objects.bulk_update(to_update, [
                    'prospect', 'appointment', 'job_id', 'client_cid', 'service',
                    'label', 'description', 'amount', 'expire_date', 'status_id',
                    'contract_file_id', 'estimate_file_id', 'add_user_id'
                ], batch_size=BATCH_SIZE)
                updated_count = len(to_update)
                self.stdout.write(self.style.SUCCESS(f"Updated {updated_count} quote records"))
                to_update.clear()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating quote records: {e}"))
                to_update.clear()
