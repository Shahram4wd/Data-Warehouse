import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from ingestion.models import MarketingSource
from ingestion.utils import parse_datetime_obj, process_batches
from tqdm import tqdm

BATCH_SIZE = 500

class Command(BaseCommand):
    help = "Import marketing sources from a Genius-exported CSV file. Default CSV path: ingestion/csv/marketing_source.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            nargs="?",
            default=os.path.join(settings.BASE_DIR, 'ingestion', 'csv', 'marketing_source.csv'),
            help="Path to the CSV file. Defaults to BASE_DIR/ingestion/csv/marketing_source.csv"
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

        source_ids = [int(row["id"]) for row in rows if row.get("id") and row["id"].isdigit()]
        existing_sources = MarketingSource.objects.in_bulk(source_ids)

        to_create = []
        to_update = []

        self.stdout.write(self.style.SUCCESS(f"Processing {len(rows)} marketing sources from {file_path}..."))

        field_mapping = {
            "id": "id",
            "label": "label",
            "type_id": "type_id",
            "description": "description",
            "start_date": "start_date",
            "end_date": "end_date",
            "add_user_id": "add_user_id",
            "add_date": "add_date",
            "is_active": "is_active",
            "is_allow_lead_modification": "is_allow_lead_modification",
        }

        update_fields = [field for field in field_mapping.values() if field != "id"]

        for row in tqdm(rows):
            try:
                source_id = int(row["id"])
                add_user_id = int(row["add_user_id"])
                fields = {
                    "label": row.get("label", ""),
                    "type_id": int(row["type_id"]) if row.get("type_id") and row["type_id"].isdigit() else None,
                    "description": row.get("description"),
                    "start_date": parse_datetime_obj(row.get("start_date")),
                    "end_date": parse_datetime_obj(row.get("end_date")),
                    "add_user_id": add_user_id,
                    "add_date": parse_datetime_obj(row.get("add_date")),
                    "is_active": row.get("is_active") == "1",
                    "is_allow_lead_modification": row.get("is_allow_lead_modification") == "1",
                }

                if source_id in existing_sources:
                    source_instance = existing_sources[source_id]
                    for attr, val in fields.items():
                        setattr(source_instance, attr, val)
                    to_update.append(source_instance)
                else:
                    fields["id"] = source_id
                    to_create.append(MarketingSource(**fields))

                if len(to_update) >= BATCH_SIZE or len(to_create) >= BATCH_SIZE:
                    process_batches(to_create, to_update, MarketingSource, update_fields, BATCH_SIZE)

            except (ValueError, KeyError) as e:
                self.stdout.write(self.style.WARNING(f"Skipping row due to error: {row}. Error: {e}"))

        # Final batch processing
        process_batches(to_create, to_update, MarketingSource, update_fields, BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS("Marketing source import completed."))
