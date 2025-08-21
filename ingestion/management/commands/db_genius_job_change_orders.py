import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_JobChangeOrder, Genius_Job
from ingestion.models.common import SyncHistory
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone
from datetime import datetime, date, timedelta, time
from typing import Optional

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download job change orders directly from the database and update the local database."
    
    def add_arguments(self, parser):
        # Standard CRM sync flags according to sync_crm_guide.md
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        parser.add_argument(
            '--force-overwrite',
            action='store_true', 
            help='Completely replace existing records'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Manual sync start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test run without database writes'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            default=0,
            help='Limit total records (0 = unlimited)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable verbose logging'
        )
        
        # Genius-specific arguments (backward compatibility)
        parser.add_argument(
            '--start-date',
            type=str,
            help='(DEPRECATED) Use --since instead. Start date for sync (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for sync (YYYY-MM-DD format)'
        )
        parser.add_argument(
            "--table",
            type=str,
            default="job_change_order",
            help="The name of the table to download data from. Defaults to 'job_change_order'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        connection = None

        try:
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data
            jobs = self._preload_jobs()
            
            # Process records in batches
            self._process_all_records(cursor, table_name, jobs)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _preload_jobs(self):
        """Preload jobs for lookup."""
        return {job.id: job for job in Genius_Job.objects.all()}
    
    def _process_all_records(self, cursor, table_name, jobs):
        """Process all records in batches."""
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_records = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))
        
        # Process records in batches
        for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
            self._process_batch_at_offset(cursor, table_name, offset, jobs)
    
    def _process_batch_at_offset(self, cursor, table_name, offset, jobs):
        """Process a batch of records starting at the specified offset."""
        # Get the batch of records including timestamp fields
        cursor.execute(f"""
            SELECT id, job_id, number, status_id, type_id, adjustment_change_order_id,
                   effective_date, total_amount, add_user_id, add_date, sold_user_id, 
                   sold_date, cancel_user_id, cancel_date, reason_id, envelope_id,
                   total_contract_amount, total_pre_change_orders_amount, signer_name, 
                   signer_email, financing_note, updated_at
            FROM {table_name}
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        rows = cursor.fetchall()
        
        # Process the batch
        self._process_batch(rows, jobs)
    
    def _process_batch(self, rows, jobs):
        """Process a batch of job change order records."""
        to_create = []
        to_update = []
        existing_records = Genius_JobChangeOrder.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Extract fields from row
                (record_id, job_id, number, status_id, type_id, adjustment_change_order_id,
                 effective_date, total_amount, add_user_id, add_date, sold_user_id, 
                 sold_date, cancel_user_id, cancel_date, reason_id, envelope_id,
                 total_contract_amount, total_pre_change_orders_amount, signer_name, 
                 signer_email, financing_note, updated_at) = row

                # Get job
                job = jobs.get(job_id)
                if not job:
                    self.stdout.write(self.style.WARNING(f"Job {job_id} not found for change order {record_id}"))
                    continue

                # Convert date fields
                if effective_date:
                    effective_date = effective_date.date() if isinstance(effective_date, datetime) else effective_date
                if add_date:
                    add_date = timezone.make_aware(add_date) if timezone.is_naive(add_date) else add_date
                if sold_date:
                    sold_date = timezone.make_aware(sold_date) if timezone.is_naive(sold_date) else sold_date
                if cancel_date:
                    cancel_date = timezone.make_aware(cancel_date) if timezone.is_naive(cancel_date) else cancel_date
                if updated_at:
                    updated_at = timezone.make_aware(updated_at) if timezone.is_naive(updated_at) else updated_at
                
                # Convert decimal fields
                total_amount = Decimal(str(total_amount)) if total_amount is not None else Decimal('0.00')
                total_contract_amount = Decimal(str(total_contract_amount)) if total_contract_amount is not None else Decimal('0.00')
                total_pre_change_orders_amount = Decimal(str(total_pre_change_orders_amount)) if total_pre_change_orders_amount is not None else Decimal('0.00')
                
                # Convert integer fields
                status_id = int(status_id) if status_id is not None else 1
                type_id = int(type_id) if type_id is not None else 1

                if record_id in existing_records:
                    # Update existing record
                    record_instance = existing_records[record_id]
                    record_instance.job = job
                    record_instance.number = number
                    record_instance.status_id = status_id
                    record_instance.type_id = type_id
                    record_instance.adjustment_change_order_id = adjustment_change_order_id
                    record_instance.effective_date = effective_date
                    record_instance.total_amount = total_amount
                    record_instance.add_user_id = add_user_id
                    record_instance.add_date = add_date
                    record_instance.sold_user_id = sold_user_id
                    record_instance.sold_date = sold_date
                    record_instance.cancel_user_id = cancel_user_id
                    record_instance.cancel_date = cancel_date
                    record_instance.reason_id = reason_id
                    record_instance.envelope_id = envelope_id
                    record_instance.total_contract_amount = total_contract_amount
                    record_instance.total_pre_change_orders_amount = total_pre_change_orders_amount
                    record_instance.signer_name = signer_name
                    record_instance.signer_email = signer_email
                    record_instance.financing_note = financing_note
                    record_instance.updated_at = updated_at
                    to_update.append(record_instance)
                else:
                    # Create new record
                    to_create.append(Genius_JobChangeOrder(
                        id=record_id,
                        job=job,
                        number=number,
                        status_id=status_id,
                        type_id=type_id,
                        adjustment_change_order_id=adjustment_change_order_id,
                        effective_date=effective_date,
                        total_amount=total_amount,
                        add_user_id=add_user_id,
                        add_date=add_date,
                        sold_user_id=sold_user_id,
                        sold_date=sold_date,
                        cancel_user_id=cancel_user_id,
                        cancel_date=cancel_date,
                        reason_id=reason_id,
                        envelope_id=envelope_id,
                        total_contract_amount=total_contract_amount,
                        total_pre_change_orders_amount=total_pre_change_orders_amount,
                        signer_name=signer_name,
                        signer_email=signer_email,
                        financing_note=financing_note,
                        updated_at=updated_at
                    ))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to process record {record_id}: {e}"))
                continue

        # Bulk create and update
        if to_create:
            Genius_JobChangeOrder.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
            self.stdout.write(self.style.SUCCESS(f"Created {len(to_create)} job change order records"))
        
        if to_update:
            Genius_JobChangeOrder.objects.bulk_update(
                to_update,
                ['job', 'number', 'status_id', 'type_id', 'adjustment_change_order_id',
                 'effective_date', 'total_amount', 'add_user_id', 'add_date', 'sold_user_id', 
                 'sold_date', 'cancel_user_id', 'cancel_date', 'reason_id', 'envelope_id',
                 'total_contract_amount', 'total_pre_change_orders_amount', 'signer_name', 
                 'signer_email', 'financing_note', 'updated_at'],
                batch_size=BATCH_SIZE
            )
            self.stdout.write(self.style.SUCCESS(f"Updated {len(to_update)} job change order records"))
