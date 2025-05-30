from django.core.management.base import BaseCommand, CommandError
from ingestion.genius.genius_client import GeniusClient
from ingestion.genius.service_sync import ServiceSync
from django.conf import settings

class Command(BaseCommand):
    help = "Sync services from Genius API. Syncs a single service if service_id is provided, otherwise syncs all services."

    def add_arguments(self, parser):
        parser.add_argument("--service_id", type=int, help="Optional: The ID of a specific service to sync", required=False)

    def handle(self, *args, **options):
        client = GeniusClient(
            settings.GENIUS_API_URL,
            settings.GENIUS_USERNAME,
            settings.GENIUS_PASSWORD
        )

        sync = ServiceSync(client)
        service_id = options.get("service_id")
        
        try:
            if service_id:
                result_id = sync.sync_single(service_id)
                self.stdout.write(self.style.SUCCESS(f"Service {result_id} synced successfully."))
            else:
                total_synced = sync.sync_all()
                self.stdout.write(self.style.SUCCESS(f"All services sync complete. Total services synced: {total_synced}"))
        except Exception as e:
            mode = f"service {service_id}" if service_id else "all services"
            raise CommandError(f"Failed to sync {mode}: {e}")