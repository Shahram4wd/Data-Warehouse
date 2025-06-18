import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from ingestion.models.genius import Genius_UserData  # Updated import
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

class Command(BaseCommand):
    help = "Import users from a Genius-exported CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)

    def handle(self, *args, **options):
        file_path = options["csv_file"]

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

        user_ids = [int(row["user_id"]) for row in rows if row.get("user_id")]
        existing_users = Genius_UserData.objects.in_bulk(user_ids)
        to_create = []
        to_update = []

        self.stdout.write(self.style.SUCCESS(f"Processing {len(rows)} users..."))

        for row in tqdm(rows):
            user_id = int(row["user_id"])
            fields = {
                "division_id": row["division_id"] or None,
                "first_name": row["first_name"] or "",
                "first_name_alt": row["first_name_alt"] or None,
                "last_name": row["last_name"] or "",
                "email": row["email"] or None,
                "personal_email": row["personal_email"] or None,
                "birth_date": parse_date(row.get("birth_date")),
                "gender_id": row["gender_id"] or None,
                "marital_status_id": row["marital_status_id"] or None,
                "time_zone_name": row["time_zone_name"] or "",
                "title_id": row["title_id"] or None,
                "manager_user_id": row["manager_user_id"] or None,
                "hired_on": parse_date(row.get("hired_on")),
                "start_date": parse_date(row.get("start_date")),
                "add_user_id": row["add_user_id"] or None,
                "add_datetime": parse_date(row.get("add_datetime")),
            }

            if user_id in existing_users:
                for attr, val in fields.items():
                    setattr(existing_users[user_id], attr, val)
                to_update.append(existing_users[user_id])
            else:
                to_create.append(Genius_UserData(id=user_id, **fields))

            # Process in batches
            if len(to_update) >= BATCH_SIZE:
                with transaction.atomic():
                    Genius_UserData.objects.bulk_update(to_update, fields.keys())
                to_update.clear()

            if len(to_create) >= BATCH_SIZE:
                with transaction.atomic():
                    Genius_UserData.objects.bulk_create(to_create, ignore_conflicts=True)
                to_create.clear()

        # Final batch
        if to_update:
            with transaction.atomic():
                Genius_UserData.objects.bulk_update(to_update, fields.keys())

        if to_create:
            with transaction.atomic():
                Genius_UserData.objects.bulk_create(to_create, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS("User import completed."))