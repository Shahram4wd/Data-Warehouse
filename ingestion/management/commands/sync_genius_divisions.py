from django.core.management.base import BaseCommand, CommandError
from ingestion.genius.genius_client import GeniusClient
from ingestion.genius.division_sync import DivisionSync
from django.conf import settings

class Command(BaseCommand):
    help = "Sync divisions from Genius API. Syncs a single division if division_id is provided, otherwise syncs all divisions."

    def add_arguments(self, parser):
        parser.add_argument("--division_id", type=int, help="Optional: The ID of a specific division to sync", required=False)

    def handle(self, *args, **options):
        client = GeniusClient(
            settings.GENIUS_API_URL,
            settings.GENIUS_USERNAME,
            settings.GENIUS_PASSWORD
        )

        sync = DivisionSync(client)
        division_id = options.get("division_id")
        
        try:
            if division_id:
                result_id = sync.sync_single(division_id)
                self.stdout.write(self.style.SUCCESS(f"Division {result_id} synced successfully."))
            else:
                total_synced = sync.sync_all()
                self.stdout.write(self.style.SUCCESS(f"All divisions sync complete. Total divisions synced: {total_synced}"))
        except Exception as e:
            mode = f"division {division_id}" if division_id else "all divisions"
            raise CommandError(f"Failed to sync {mode}: {e}")