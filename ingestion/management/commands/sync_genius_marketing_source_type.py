import requests
from django.core.management.base import BaseCommand
from ingestion.models import MarketingSourceType
from ingestion.utils import parse_datetime_obj, process_batches
from tqdm import tqdm

BATCH_SIZE = 500

class Command(BaseCommand):
    help = "Sync marketing source types from an external API."

    def handle(self, *args, **options):
        api_url = "https://api.example.com/genius/marketing_source_type"
        response = requests.get(api_url)

        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"Failed to fetch data from API: {response.status_code}"))
            return

        source_types = response.json()
        type_ids = [source_type["id"] for source_type in source_types]
        existing_types = MarketingSourceType.objects.in_bulk(type_ids)

        to_create = []
        to_update = []

        self.stdout.write(self.style.SUCCESS(f"Processing {len(source_types)} marketing source types from API..."))

        for source_type in tqdm(source_types):
            try:
                type_id = source_type["id"]
                fields = {
                    "label": source_type.get("label", ""),
                    "description": source_type.get("description"),
                    "is_active": source_type.get("is_active", False),
                    "list_order": source_type.get("list_order"),
                }

                if type_id in existing_types:
                    type_instance = existing_types[type_id]
                    for attr, val in fields.items():
                        setattr(type_instance, attr, val)
                    to_update.append(type_instance)
                else:
                    fields["id"] = type_id
                    to_create.append(MarketingSourceType(**fields))

                if len(to_update) >= BATCH_SIZE or len(to_create) >= BATCH_SIZE:
                    process_batches(to_create, to_update, MarketingSourceType, fields.keys(), BATCH_SIZE)

            except (ValueError, KeyError) as e:
                self.stdout.write(self.style.WARNING(f"Skipping source type due to error: {source_type}. Error: {e}"))

        # Final batch processing
        process_batches(to_create, to_update, MarketingSourceType, fields.keys(), BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS("Marketing source type sync completed."))
