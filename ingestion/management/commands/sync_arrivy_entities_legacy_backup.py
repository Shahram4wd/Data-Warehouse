import asyncio
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from ingestion.models.arrivy import Arrivy_Entity, Arrivy_SyncHistory
from ingestion.arrivy.arrivy_client import ArrivyClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 100

class Command(BaseCommand):
    help = "Sync individual crew members (entities) from Arrivy API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental sync"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Show debug output"
        )
        parser.add_argument(
            "--pages",
            type=int,
            default=0,
            help="Maximum number of pages to process (0 for unlimited)"
        )
        parser.add_argument(
            "--lastmodifieddate",
            type=str,
            help="Filter records modified after this date (YYYY-MM-DD format)"
        )

    def handle(self, *args, **options):
        """Main command handler."""
        try:
            # Configure logging level
            if options.get("debug"):
                logging.getLogger().setLevel(logging.DEBUG)
                logging.getLogger("arrivy_client").setLevel(logging.DEBUG)

            # Extract options
            full_sync = options.get("full", False)
            max_pages = options.get("pages", 0)
            lastmodifieddate = options.get("lastmodifieddate")

            self.stdout.write("Starting Arrivy entities sync...")

            # Run the async sync process
            total_processed = asyncio.run(self.sync_entities(
                full_sync=full_sync,
                max_pages=max_pages,
                lastmodifieddate=lastmodifieddate
            ))

            self.stdout.write(
                self.style.SUCCESS(
                    f"Arrivy entities sync complete. Processed {total_processed} entities total."
                )
            )

        except Exception as e:
            logger.exception("Error during Arrivy entities sync")
            raise CommandError(f"Sync failed: {str(e)}")

    def process_entities_sync(self, entities):
        """Synchronously process a batch of entities inside a transaction."""
        with transaction.atomic():
            for entity in entities:
                created_at = entity.get("created_at") or timezone.now()
                Arrivy_Entity.objects.update_or_create(
                    id=entity["id"],
                    defaults={
                        "name": entity.get("name"),
                        "username": entity.get("username"),
                        "type": entity.get("type"),
                        "external_id": entity.get("external_id"),
                        "external_type": entity.get("external_type"),
                        "email": entity.get("email"),
                        "phone": entity.get("phone"),
                        "image_id": entity.get("image_id"),
                        "group_id": entity.get("group_id"),
                        "permission_groups": entity.get("permission_groups"),
                        "skill_details": entity.get("skill_details"),
                        "is_active": entity.get("is_active"),
                        "created_at": created_at,
                    },
                )

    async def sync_entities(self, full_sync=False, max_pages=0, lastmodifieddate=None):
        """Sync entities from Arrivy API."""
        client = ArrivyClient()

        # Get the last sync time
        sync_type = "entities"

        # Priority: 1) --lastmodifieddate parameter, 2) database last sync, 3) full sync
        if lastmodifieddate:
            try:
                last_sync = datetime.strptime(lastmodifieddate, "%Y-%m-%d")
                last_sync = timezone.make_aware(last_sync)
                self.stdout.write(f"Using provided lastmodifieddate filter: {lastmodifieddate}")
            except ValueError:
                raise CommandError("Invalid date format. Use YYYY-MM-DD")
        elif not full_sync:
            try:
                sync_history = await sync_to_async(Arrivy_SyncHistory.objects.get)(sync_type=sync_type)
                last_sync = sync_history.last_synced_at
                self.stdout.write(f"Performing delta sync since {last_sync}")
            except Arrivy_SyncHistory.DoesNotExist:
                last_sync = None
                self.stdout.write("No previous sync found, performing full sync")
        else:
            last_sync = None

        # Fetch entities from the API
        page = 1
        total_processed = 0

        while True:
            self.stdout.write(f"Fetching page {page}...")
            response = await client.get_entities(last_sync=last_sync, page=page)

            if not response or not response.get("data"):
                self.stdout.write("No more data to process.")
                break

            entities = response["data"]

            # Process each entity batch in a sync context
            await sync_to_async(self.process_entities_sync)(entities)

            total_processed += len(entities)
            self.stdout.write(f"Processed {len(entities)} entities on page {page}.")

            # Check if we should stop
            if max_pages and page >= max_pages:
                self.stdout.write("Reached maximum page limit.")
                break

            # Remove next_page check; just increment page
            page += 1

        # Update sync history
        await sync_to_async(Arrivy_SyncHistory.objects.update_or_create)(
            sync_type=sync_type,
            defaults={"last_synced_at": timezone.now()},
        )

        return total_processed
