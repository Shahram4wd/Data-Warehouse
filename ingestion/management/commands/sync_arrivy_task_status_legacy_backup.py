import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from ingestion.models.arrivy import Arrivy_TaskStatus, Arrivy_SyncHistory
from ingestion.arrivy.arrivy_client import ArrivyClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync task statuses from Arrivy API"

    def handle(self, *args, **options):
        try:
            self.stdout.write("Starting Arrivy task status sync...")            # Fetch task statuses from the API
            client = ArrivyClient()
            response = client.get_task_statuses()

            # Handle both dictionary and list responses
            if isinstance(response, dict):
                statuses = response.get("data", [])
            elif isinstance(response, list):
                statuses = response
            else:
                statuses = []

            if not statuses:
                self.stdout.write("No task statuses to process.")
                return

            # Process each task status
            with transaction.atomic():
                for status in statuses:
                    Arrivy_TaskStatus.objects.update_or_create(
                        id=status["id"],
                        defaults={
                            "name": status.get("name"),
                            "description": status.get("description"),
                            "is_active": status.get("is_active", True),
                            "created_time": status.get("created_time"),
                            "updated_time": status.get("updated_time"),
                        },
                    )            # Update sync history
            Arrivy_SyncHistory.objects.update_or_create(
                sync_type="task_statuses",
                defaults={"last_synced_at": timezone.now()},
            )

            self.stdout.write(
                self.style.SUCCESS(f"Arrivy task status sync complete. Processed {len(statuses)} statuses.")
            )

        except Exception as e:
            logger.exception("Error during Arrivy task status sync")
            raise CommandError(f"Sync failed: {str(e)}")
