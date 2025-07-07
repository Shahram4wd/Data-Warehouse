import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from ingestion.models.salespro import SalesPro_Appointment, SalesPro_SyncHistory
from ingestion.salespro.base_processor import BaseSalesProProcessor
from tqdm import tqdm
from django.db import transaction
from django.utils import timezone

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))  # Default to 500 if not set


class Command(BaseCommand, BaseSalesProProcessor):
    help = "Import appointment/sales data from a SalesPro CSV export file"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        BaseSalesProProcessor.__init__(self, 'csv_appointments')

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the SalesPro CSV file")
        parser.add_argument(
            "--dry-run", 
            action="store_true", 
            help="Show what would be imported without making changes"
        )

    def handle(self, *args, **options):
        file_path = options["csv_file"]
        dry_run = options.get("dry_run", False)

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Start sync tracking
        if not dry_run:
            sync_history = self.start_sync(file_path)

        try:
            # Read CSV file
            with open(file_path, newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)

            self.stdout.write(self.style.SUCCESS(f"Found {len(rows)} records in CSV"))

            if dry_run:
                self.show_sample_data(rows[:5])
                return

            # Get existing records for bulk operations
            appointment_ids = [row["_id"] for row in rows if row.get("_id")]
            existing_appointments = SalesPro_Appointment.objects.in_bulk(appointment_ids)
            
            to_create = []
            to_update = []
            created_count = 0
            updated_count = 0

            self.stdout.write(self.style.SUCCESS(f"Processing {len(rows)} appointments..."))

            for row in tqdm(rows, desc="Processing appointments"):
                appointment_id = row["_id"]
                if not appointment_id:
                    continue

                # Parse CSV data
                fields = {
                    "created_at": self.parse_datetime(row.get("_created_at")),
                    "updated_at": self.parse_datetime(row.get("_updated_at")),
                    "is_sale": self.parse_boolean(row.get("isSale")),
                    "result_full_string": row.get("resultFullString") or None,
                    "customer_last_name": row.get("customerLastName") or None,
                    "customer_first_name": row.get("customerFirstName") or None,
                    "customer_estimate_name": row.get("estimateName") or None,
                    "salesrep_email": row.get("salesRepEmail") or None,
                    "salesrep_first_name": row.get("salesRepFirstName") or None,
                    "salesrep_last_name": row.get("salesRepLastName") or None,
                    "sale_amount": self.parse_decimal(row.get("saleAmount")),
                }

                if appointment_id in existing_appointments:
                    # Update existing record
                    appointment = existing_appointments[appointment_id]
                    for attr, val in fields.items():
                        setattr(appointment, attr, val)
                    to_update.append(appointment)
                else:
                    # Create new record
                    to_create.append(SalesPro_Appointment(id=appointment_id, **fields))

                # Process in batches for better performance
                if len(to_update) >= BATCH_SIZE:
                    with transaction.atomic():
                        SalesPro_Appointment.objects.bulk_update(to_update, fields.keys())
                    updated_count += len(to_update)
                    to_update.clear()

                if len(to_create) >= BATCH_SIZE:
                    with transaction.atomic():
                        SalesPro_Appointment.objects.bulk_create(to_create, ignore_conflicts=True)
                    created_count += len(to_create)
                    to_create.clear()

            # Process final batch
            if to_update:
                with transaction.atomic():
                    SalesPro_Appointment.objects.bulk_update(to_update, fields.keys())
                updated_count += len(to_update)

            if to_create:
                with transaction.atomic():
                    SalesPro_Appointment.objects.bulk_create(to_create, ignore_conflicts=True)
                created_count += len(to_create)

            # Complete sync tracking
            self.complete_sync(
                records_processed=len(rows),
                records_created=created_count,
                records_updated=updated_count
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Import completed successfully!\n"
                    f"Records processed: {len(rows)}\n"
                    f"Records created: {created_count}\n"
                    f"Records updated: {updated_count}"
                )
            )

        except Exception as e:
            error_msg = f"Import failed: {str(e)}"
            if not dry_run:
                self.fail_sync(error_msg)
            self.stdout.write(self.style.ERROR(error_msg))
            raise

    def show_sample_data(self, sample_rows):
        """Show sample data for dry run"""
        self.stdout.write(self.style.SUCCESS("\nSample records that would be imported:"))
        self.stdout.write("-" * 80)
        
        for i, row in enumerate(sample_rows, 1):
            self.stdout.write(f"\nRecord {i}:")
            self.stdout.write(f"  ID: {row.get('_id')}")
            self.stdout.write(f"  Created: {row.get('_created_at')}")
            self.stdout.write(f"  Is Sale: {row.get('isSale')}")
            self.stdout.write(f"  Customer: {row.get('customerFirstName')} {row.get('customerLastName')}")
            self.stdout.write(f"  Sales Rep: {row.get('salesRepFirstName')} {row.get('salesRepLastName')} ({row.get('salesRepEmail')})")
            self.stdout.write(f"  Sale Amount: ${row.get('saleAmount') or '0'}")
            
        self.stdout.write("\n" + "-" * 80)
        self.stdout.write("Run without --dry-run to perform the actual import.")
