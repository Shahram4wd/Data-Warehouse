import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from ingestion.models.genius import Genius_MarketingSourceType
from ingestion.utils import parse_datetime_obj, process_batches
from tqdm import tqdm

BATCH_SIZE = 500

class Command(BaseCommand):
    help = "Import marketing source types from a Genius-exported CSV file. Default CSV path: ingestion/csv/marketing_source_type.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            nargs="?",
            default=os.path.join(settings.BASE_DIR, 'ingestion', 'csv', 'marketing_source_type.csv'),
            help="Path to the CSV file. Defaults to BASE_DIR/ingestion/csv/marketing_source_type.csv"
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

        type_ids = [int(row["id"]) for row in rows if row.get("id") and row["id"].isdigit()]
        existing_types = Genius_MarketingSourceType.objects.in_bulk(type_ids)

        to_create = []
        to_update = []

        self.stdout.write(self.style.SUCCESS(f"Processing {len(rows)} marketing source types from {file_path}..."))

        field_mapping = {
            "id": "id",
            "label": "label",
            "description": "description",
            "is_active": "is_active",
            "list_order": "list_order",
        }

        update_fields = [field for field in field_mapping.values() if field != "id"]

        for row in tqdm(rows):
            try:
                type_id = int(row["id"])
                fields = {
                    "label": row.get("label", ""),
                    "description": row.get("description"),
                    "is_active": row.get("is_active") == "1",
                    "list_order": int(row["list_order"]) if row.get("list_order") and row["list_order"].isdigit() else None,
                }

                if type_id in existing_types:
                    type_instance = existing_types[type_id]
                    for attr, val in fields.items():
                        setattr(type_instance, attr, val)
                    to_update.append(type_instance)
                else:
                    fields["id"] = type_id
                    to_create.append(Genius_MarketingSourceType(**fields))

                if len(to_update) >= BATCH_SIZE or len(to_create) >= BATCH_SIZE:
                    process_batches(to_create, to_update, Genius_MarketingSourceType, update_fields, BATCH_SIZE)

            except (ValueError, KeyError) as e:
                self.stdout.write(self.style.WARNING(f"Skipping row due to error: {row}. Error: {e}"))

        # Final batch processing
        process_batches(to_create, to_update, Genius_MarketingSourceType, update_fields, BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS("Marketing source type import completed."))
