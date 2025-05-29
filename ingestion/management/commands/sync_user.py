from django.core.management.base import BaseCommand, CommandError
from ingestion.genius.genius_client import GeniusClient
from ingestion.genius.user_data_single_sync import sync_single_user
from django.conf import settings

class Command(BaseCommand):
    help = "Fetch and sync a single user by ID from Genius"

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=int, help="The ID of the user to sync")

    def handle(self, *args, **options):
        user_id = options["user_id"]

        client = GeniusClient(
            settings.GENIUS_API_URL,
            settings.GENIUS_USERNAME,
            settings.GENIUS_PASSWORD
        )

        try:
            result_id = sync_single_user(client, user_id)
            self.stdout.write(self.style.SUCCESS(f"User {result_id} synced successfully."))
        except Exception as e:
            raise CommandError(f"Failed to sync user {user_id}: {e}")
