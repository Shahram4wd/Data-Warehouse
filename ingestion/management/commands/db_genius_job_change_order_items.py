import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_JobChangeOrderItem, Genius_JobChangeOrder
from ingestion.models.common import SyncHistory
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone
from datetime import datetime, date, timedelta, time
from typing import Optional

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download job change order items directly from the database and update the local database."
    
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
            default="job_change_order_item",
            help="The name of the table to download data from. Defaults to 'job_change_order_item'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        connection = None

        try:
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data
            change_orders = self._preload_change_orders()
            
            # Process records in batches
            self._process_all_records(cursor, table_name, change_orders)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _preload_change_orders(self):
        """Preload job change orders for lookup."""
        return {co.id: co for co in Genius_JobChangeOrder.objects.all()}
    
    def _process_all_records(self, cursor, table_name, change_orders):
        """Process all records in batches."""
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_records = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))
        
        # Process records in batches
        for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
            self._process_batch_at_offset(cursor, table_name, offset, change_orders)
    
    def _process_batch_at_offset(self, cursor, table_name, offset, change_orders):
        """Process a batch of records starting at the specified offset."""
        # Get the batch of records including timestamp fields
        cursor.execute(f"""
            SELECT id, change_order_id, description, amount, created_at, updated_at
            FROM {table_name}
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        rows = cursor.fetchall()
        
        # Process the batch
        self._process_batch(rows, change_orders)
    
    def _process_batch(self, rows, change_orders):
        """Process a batch of job change order item records."""
        to_create = []
        to_update = []
        existing_records = Genius_JobChangeOrderItem.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Extract fields from row
                record_id, change_order_id, description, amount, created_at, updated_at = row

                # Get change order
                change_order = change_orders.get(change_order_id)
                if not change_order:
                    self.stdout.write(self.style.WARNING(f"Change order {change_order_id} not found for item {record_id}"))
                    continue

                # Convert timestamps to timezone-aware datetimes
                if created_at:
                    created_at = timezone.make_aware(created_at) if timezone.is_naive(created_at) else created_at
                if updated_at:
                    updated_at = timezone.make_aware(updated_at) if timezone.is_naive(updated_at) else updated_at
                
                # Convert amount to Decimal
                amount = Decimal(str(amount)) if amount is not None else Decimal('0.00')

                if record_id in existing_records:
                    # Update existing record
                    record_instance = existing_records[record_id]
                    record_instance.change_order = change_order
                    record_instance.description = description
                    record_instance.amount = amount
                    record_instance.created_at = created_at
                    record_instance.updated_at = updated_at
                    to_update.append(record_instance)
                else:
                    # Create new record
                    to_create.append(Genius_JobChangeOrderItem(
                        id=record_id,
                        change_order=change_order,
                        description=description,
                        amount=amount,
                        created_at=created_at,
                        updated_at=updated_at
                    ))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to process record {record_id}: {e}"))
                continue

        # Bulk create and update
        if to_create:
            Genius_JobChangeOrderItem.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
            self.stdout.write(self.style.SUCCESS(f"Created {len(to_create)} job change order item records"))
        
        if to_update:
            Genius_JobChangeOrderItem.objects.bulk_update(
                to_update,
                ['change_order', 'description', 'amount', 'created_at', 'updated_at'],
                batch_size=BATCH_SIZE
            )
            self.stdout.write(self.style.SUCCESS(f"Updated {len(to_update)} job change order item records"))
