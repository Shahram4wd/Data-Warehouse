import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from ingestion.models import Appointment
from ingestion.utils import parse_datetime_obj, process_batches
from tqdm import tqdm

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))  # Default to 500 if not set

class Command(BaseCommand):
    help = "Import appointments from a Genius-exported CSV file. Default CSV path: ingestion/csv/appointments.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            nargs="?",
            default=os.path.join(settings.BASE_DIR, 'ingestion', 'csv', 'appointments.csv'),
            help="Path to the CSV file. Defaults to BASE_DIR/ingestion/csv/appointments.csv"
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

        appointment_ids = [int(row["id"]) for row in rows if row.get("id") and row["id"].isdigit()]
        existing_appointments = Appointment.objects.in_bulk(appointment_ids)

        to_create = []
        to_update = []

        self.stdout.write(self.style.SUCCESS(f"Processing {len(rows)} appointments from {file_path}..."))

        field_mapping = {
            "id": "id",
            "prospect_id": "prospect_id",
            "user_id": "user_id",
            "type_id": "type_id",
            "date": "date",
            "time": "time",
            "duration": "duration",
            "address1": "address1",
            "address2": "address2",
            "city": "city",
            "state": "state",
            "zip": "zip",
            "email": "email",
            "notes": "notes",
            "add_user_id": "add_user_id",
            "add_date": "add_date",
            "assign_date": "assign_date",
            "confirm_user_id": "confirm_user_id",
            "confirm_date": "confirm_date",
            "confirm_with": "confirm_with",
            "spouses_present": "spouses_present",
            "is_complete": "is_complete",
            "complete_outcome_id": "complete_outcome_id",
            "complete_user_id": "complete_user_id",
            "complete_date": "complete_date",
        }

        update_fields = [field for field in field_mapping.values() if field != "id"]

        for row in tqdm(rows):
            try:
                appointment_id = int(row["id"])
                fields = {
                    "prospect_id": int(row["prospect_id"]) if row.get("prospect_id") and row["prospect_id"].isdigit() else None,
                    "user_id": int(row["user_id"]) if row.get("user_id") and row["user_id"].isdigit() else None,
                    "type_id": int(row["type_id"]) if row.get("type_id") and row["type_id"].isdigit() else None,
                    "date": parse_datetime_obj(row.get("date")),
                    "time": parse_datetime_obj(row.get("time")),
                    "duration": parse_datetime_obj(row.get("duration")),
                    "address1": row.get("address1", ""),
                    "address2": row.get("address2", ""),
                    "city": row.get("city", ""),
                    "state": row.get("state", ""),
                    "zip": row.get("zip", ""),
                    "email": row.get("email"),
                    "notes": row.get("notes"),
                    "add_user_id": int(row["add_user_id"]) if row.get("add_user_id") and row["add_user_id"].isdigit() else None,
                    "add_date": parse_datetime_obj(row.get("add_date")),
                    "assign_date": parse_datetime_obj(row.get("assign_date")),
                    "confirm_user_id": int(row["confirm_user_id"]) if row.get("confirm_user_id") and row["confirm_user_id"].isdigit() else None,
                    "confirm_date": parse_datetime_obj(row.get("confirm_date")),
                    "confirm_with": row.get("confirm_with"),
                    "spouses_present": row.get("spouses_present") == "1",
                    "is_complete": row.get("is_complete") == "1",
                    "complete_outcome_id": int(row["complete_outcome_id"]) if row.get("complete_outcome_id") and row["complete_outcome_id"].isdigit() else None,
                    "complete_user_id": int(row["complete_user_id"]) if row.get("complete_user_id") and row["complete_user_id"].isdigit() else None,
                    "complete_date": parse_datetime_obj(row.get("complete_date")),
                }

                if appointment_id in existing_appointments:
                    appointment_instance = existing_appointments[appointment_id]
                    for attr, val in fields.items():
                        setattr(appointment_instance, attr, val)
                    to_update.append(appointment_instance)
                else:
                    fields["id"] = appointment_id
                    to_create.append(Appointment(**fields))

                if len(to_update) >= BATCH_SIZE or len(to_create) >= BATCH_SIZE:
                    process_batches(to_create, to_update, Appointment, update_fields, BATCH_SIZE)

            except (ValueError, KeyError) as e:
                self.stdout.write(self.style.WARNING(f"Skipping row due to error: {row}. Error: {e}"))

        # Final batch processing
        process_batches(to_create, to_update, Appointment, update_fields, BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS("Appointment import completed."))
