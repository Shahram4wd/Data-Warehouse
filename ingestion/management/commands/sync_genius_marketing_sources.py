from django.core.management.base import BaseCommand, CommandError
from ingestion.genius.genius_client import GeniusClient
from ingestion.genius.marketing_source_sync import MarketingSourceSync
from django.conf import settings

class Command(BaseCommand):
    help = "Sync marketing sources from Genius API. Syncs a single source if source_id is provided, otherwise syncs all sources."

    def add_arguments(self, parser):
        parser.add_argument("--source_id", type=int, help="Optional: The ID of a specific marketing source to sync", required=False)

    def handle(self, *args, **options):
        client = GeniusClient(
            settings.GENIUS_API_URL,
            settings.GENIUS_USERNAME,
            settings.GENIUS_PASSWORD
        )

        sync = MarketingSourceSync(client)
        source_id = options.get("source_id")
        
        try:
            if source_id:
                result_id = sync.sync_single(source_id)
                self.stdout.write(self.style.SUCCESS(f"Marketing source {result_id} synced successfully."))
            else:
                total_synced = sync.sync_all()
                self.stdout.write(self.style.SUCCESS(f"All marketing sources sync complete. Total sources synced: {total_synced}"))
        except Exception as e:
            mode = f"marketing source {source_id}" if source_id else "all marketing sources"
            raise CommandError(f"Failed to sync {mode}: {e}")