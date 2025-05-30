from django.core.management.base import BaseCommand, CommandError
from ingestion.genius.genius_client import GeniusClient
from ingestion.genius.prospect_sync import ProspectSync
from django.conf import settings

class Command(BaseCommand):
    help = "Sync prospects from Genius API. Syncs a single prospect if prospect_id is provided, otherwise syncs all prospects."

    def add_arguments(self, parser):
        parser.add_argument("--prospect_id", type=int, help="Optional: The ID of a specific prospect to sync", required=False)

    def handle(self, *args, **options):
        client = GeniusClient(
            settings.GENIUS_API_URL,
            settings.GENIUS_USERNAME,
            settings.GENIUS_PASSWORD
        )

        sync = ProspectSync(client)
        prospect_id = options.get("prospect_id")
        
        try:
            if prospect_id:
                result_id = sync.sync_single(prospect_id)
                self.stdout.write(self.style.SUCCESS(f"Prospect {result_id} synced successfully."))
            else:
                total_synced = sync.sync_all()
                self.stdout.write(self.style.SUCCESS(f"All prospects sync complete. Total prospects synced: {total_synced}"))
        except Exception as e:
            mode = f"prospect {prospect_id}" if prospect_id else "all prospects"
            raise CommandError(f"Failed to sync {mode}: {e}")