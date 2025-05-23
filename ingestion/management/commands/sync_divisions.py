from django.core.management.base import BaseCommand
from ingestion.genius.division_sync import sync_divisions

class Command(BaseCommand):
    help = "Sync divisions from Genius"

    def handle(self, *args, **kwargs):
        sync_divisions()
        self.stdout.write(self.style.SUCCESS("Divisions synced successfully."))
