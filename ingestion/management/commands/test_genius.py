from django.core.management.base import BaseCommand
from ingestion.genius.genius_client import GeniusClient
from django.conf import settings

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        client = GeniusClient(
            settings.GENIUS_API_URL,
            settings.GENIUS_USERNAME,
            settings.GENIUS_PASSWORD
        )
        prospects = client.get_prospects()
        self.stdout.write(self.style.SUCCESS(f"Fetched {len(prospects)} prospects"))
