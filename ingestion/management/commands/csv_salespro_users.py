import csv
import os
import re
from datetime import datetime
from django.core.management.base import BaseCommand
from ingestion.models.salespro import SalesPro_Users
from tqdm import tqdm
from django.db import transaction

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))  # Default to 500 if not set

def parse_date(value):
    """Convert common date formats to YYYY-MM-DD."""
    if not value or not str(value).strip():
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None

def parse_office_id(office_string):
    """Extract office ID from the assigned office string."""
    if not office_string:
        return None
    match = re.search(r'\(\s*([a-zA-Z0-9]+)\s*\)', office_string)
    return match.group(1) if match else None

class Command(BaseCommand):
    help = "Import users from a SalesPro-exported CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to the SalesPro users CSV file"
        )

    def handle(self, *args, **options):
        file_path = options["csv_file"]

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found at {file_path}"))
            return

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

        if not rows:
            self.stdout.write(self.style.WARNING("CSV file is empty."))
            return

        user_ids = [row["User Object ID"] for row in rows if row.get("User Object ID")]
        existing_users = SalesPro_Users.objects.in_bulk(user_ids)

        to_create = []
        to_update = []

        self.stdout.write(self.style.SUCCESS(f"Processing {len(rows)} SalesPro users..."))

        for row in tqdm(rows):
            user_id = row["User Object ID"]
            fields = {
                "first_name": row.get("First Name", ""),
                "last_name": row.get("Last Name", ""),
                "username": row.get("Username", ""),
                "email": row.get("Email", ""),
                "last_login": parse_date(row.get("Last Login")),
                "is_active": row.get("Active/Inactive", "").upper() == "TRUE",
                "send_credit_apps": row.get("Send Credit Apps", "").upper() == "TRUE",
                "search_other_users_estimates": row.get("Search Other Users Estimates", "").upper() == "TRUE",
                "assigned_office": row.get("Assigned Office", ""),
                "office_id": parse_office_id(row.get("Assigned Office")),
                "license_number": row.get("License Number", ""),
                "additional_amount": float(row.get("Additional Amount", 0) or 0),
                "unique_identifier": row.get("Unique Identifier", ""),
                "job_representative_id": row.get("Job Representative ID", ""),
            }

            if user_id in existing_users:
                for attr, val in fields.items():
                    setattr(existing_users[user_id], attr, val)
                to_update.append(existing_users[user_id])
            else:
                to_create.append(SalesPro_Users(user_object_id=user_id, **fields))

            # Process in batches
            if len(to_update) >= BATCH_SIZE:
                with transaction.atomic():
                    SalesPro_Users.objects.bulk_update(to_update, fields.keys())
                to_update.clear()

            if len(to_create) >= BATCH_SIZE:
                with transaction.atomic():
                    SalesPro_Users.objects.bulk_create(to_create, ignore_conflicts=True)
                to_create.clear()

        # Final batch
        if to_update:
            with transaction.atomic():
                SalesPro_Users.objects.bulk_update(to_update, fields.keys())

        if to_create:
            with transaction.atomic():
                SalesPro_Users.objects.bulk_create(to_create, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS("SalesPro user import completed."))
