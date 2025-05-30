from django.core.management.base import BaseCommand, CommandError
from ingestion.genius.genius_client import GeniusClient
from ingestion.genius.user_sync import UserSync
from django.conf import settings

class Command(BaseCommand):
    help = "Sync users from Genius API. Syncs a single user if user_id is provided, otherwise syncs all users."

    def add_arguments(self, parser):
        parser.add_argument("--user_id", type=int, help="Optional: The ID of a specific user to sync", required=False)

    def handle(self, *args, **options):
        client = GeniusClient(
            settings.GENIUS_API_URL,
            settings.GENIUS_USERNAME,
            settings.GENIUS_PASSWORD
        )

        sync = UserSync(client)
        user_id = options.get("user_id")
        
        try:
            if user_id:
                result_id = sync.sync_single(user_id)
                self.stdout.write(self.style.SUCCESS(f"User {result_id} synced successfully."))
            else:
                total_synced = sync.sync_all()
                self.stdout.write(self.style.SUCCESS(f"All users sync complete. Total users synced: {total_synced}"))
        except Exception as e:
            mode = f"user {user_id}" if user_id else "all users"
            raise CommandError(f"Failed to sync {mode}: {e}")