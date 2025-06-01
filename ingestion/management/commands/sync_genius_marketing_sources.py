import requests
from django.core.management.base import BaseCommand
from ingestion.models import MarketingSource
from ingestion.utils import parse_datetime_obj, process_batches
from tqdm import tqdm

BATCH_SIZE = 500

class Command(BaseCommand):
    help = "Sync Genius marketing sources from an external API."

    def handle(self, *args, **options):
        api_url = "https://api.example.com/genius/marketing_sources"
        response = requests.get(api_url)

        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"Failed to fetch data from API: {response.status_code}"))
            return

        sources = response.json()
        source_ids = [source["id"] for source in sources]
        existing_sources = MarketingSource.objects.in_bulk(source_ids)

        to_create = []
        to_update = []

        self.stdout.write(self.style.SUCCESS(f"Processing {len(sources)} marketing sources from API..."))

        for source in tqdm(sources):
            try:
                source_id = source["id"]
                fields = {
                    "label": source.get("label", ""),
                    "type_id": source.get("type_id"),
                    "description": source.get("description"),
                    "start_date": parse_datetime_obj(source.get("start_date")),
                    "end_date": parse_datetime_obj(source.get("end_date")),
                    "add_user_id": source.get("add_user_id"),
                    "add_date": parse_datetime_obj(source.get("add_date")),
                    "is_active": source.get("is_active", False),
                    "is_allow_lead_modification": source.get("is_allow_lead_modification", False),
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
                    process_batches(to_create, to_update, MarketingSource, fields.keys(), BATCH_SIZE)

            except (ValueError, KeyError) as e:
                self.stdout.write(self.style.WARNING(f"Skipping source due to error: {source}. Error: {e}"))

        # Final batch processing
        process_batches(to_create, to_update, MarketingSource, fields.keys(), BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS("Marketing source sync completed."))