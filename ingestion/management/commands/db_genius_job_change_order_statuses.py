import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_JobChangeOrderStatus
from ingestion.models.common import SyncHistory
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone
from datetime import datetime, date, timedelta, time
from typing import Optional

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download job change order statuses directly from the database and update the local database."
    
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
            default="job_change_order_status",
            help="The name of the table to download data from. Defaults to 'job_change_order_status'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        connection = None

        try:
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Process records in batches
            self._process_all_records(cursor, table_name)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _process_all_records(self, cursor, table_name):
        """Process all records in batches."""
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_records = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))
        
        # Process records in batches
        for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
            self._process_batch_at_offset(cursor, table_name, offset)
    
    def _process_batch_at_offset(self, cursor, table_name, offset):
        """Process a batch of records starting at the specified offset."""
        # Get the batch of records
        cursor.execute(f"""
            SELECT id, label, is_selectable
            FROM {table_name}
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        rows = cursor.fetchall()
        
        # Process the batch
        self._process_batch(rows)
    
    def _process_batch(self, rows):
        """Process a batch of job change order status records."""
        to_create = []
        to_update = []
        existing_records = Genius_JobChangeOrderStatus.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Extract fields from row
                record_id, label, is_selectable = row

                # Convert is_selectable to SmallIntegerField
                is_selectable = int(is_selectable) if is_selectable is not None else 1

                if record_id in existing_records:
                    # Update existing record
                    record_instance = existing_records[record_id]
                    record_instance.label = label
                    record_instance.is_selectable = is_selectable
                    to_update.append(record_instance)
                else:
                    # Create new record
                    to_create.append(Genius_JobChangeOrderStatus(
                        id=record_id,
                        label=label,
                        is_selectable=is_selectable
                    ))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to process record {record_id}: {e}"))
                continue

        # Bulk create and update
        if to_create:
            Genius_JobChangeOrderStatus.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
            self.stdout.write(self.style.SUCCESS(f"Created {len(to_create)} job change order status records"))
        
        if to_update:
            Genius_JobChangeOrderStatus.objects.bulk_update(
                to_update,
                ['label', 'is_selectable'],
                batch_size=BATCH_SIZE
            )
            self.stdout.write(self.style.SUCCESS(f"Updated {len(to_update)} job change order status records"))
