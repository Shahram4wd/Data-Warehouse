from django.core.management.base import BaseCommand
from ingestion.genius.genius_client import GeniusClient
from ingestion.genius.user_data_sync import sync_user_data
from django.conf import settings

class Command(BaseCommand):
    help = "Fetch and sync user data from Genius"

    def handle(self, *args, **kwargs):
        client = GeniusClient(
            settings.GENIUS_API_URL,
            settings.GENIUS_USERNAME,
            settings.GENIUS_PASSWORD
        )

        count = sync_user_data(client)
        self.stdout.write(self.style.SUCCESS(f"Synced {count} user records"))
