import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from ingestion.models import Arrivy_LocationReport, Arrivy_SyncHistory
from ingestion.arrivy.arrivy_client import ArrivyClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync location reports from Arrivy API"

    def handle(self, *args, **options):
        try:
            self.stdout.write("Starting Arrivy location reports sync...")

            # Fetch location reports from the API
            client = ArrivyClient()
            response = client.get_location_reports()

            if not response or not response.get("data"):
                self.stdout.write("No location reports to process.")
                return

            reports = response["data"]

            # Process each location report
            with transaction.atomic():
                for report in reports:
                    Arrivy_LocationReport.objects.update_or_create(
                        id=report["id"],
                        defaults={
                            "task_id": report.get("task_id"),
                            "entity_id": report.get("entity_id"),
                            "latitude": report.get("latitude"),
                            "longitude": report.get("longitude"),
                            "timestamp": report.get("timestamp"),
                        },
                    )

            # Update sync history
            Arrivy_SyncHistory.objects.update_or_create(
                endpoint="location_reports",
                defaults={"last_synced_at": timezone.now(), "total_records": len(reports)},
            )

            self.stdout.write(
                self.style.SUCCESS(f"Arrivy location reports sync complete. Processed {len(reports)} reports.")
            )

        except Exception as e:
            logger.exception("Error during Arrivy location reports sync")
            raise CommandError(f"Sync failed: {str(e)}")
