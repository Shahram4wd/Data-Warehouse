"""
Management command to sync HubSpot Genius Users
Follows import_refactoring.md enterprise architecture standards
"""
import asyncio
from django.core.management.base import BaseCommand
from ingestion.sync.hubspot.engines.genius_users import HubSpotGeniusUsersSyncEngine

class Command(BaseCommand):
    help = "Sync HubSpot Genius Users (custom object 2-42119425)"

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=100, help='Batch size for API fetches')
        parser.add_argument('--dry-run', action='store_true', help='Run without writing to DB')
        parser.add_argument('--api-token', type=str, default=None, help='Override HubSpot API token')
        parser.add_argument('--max-records', type=int, default=0, help='Maximum number of records to sync (0 = all)')
        parser.add_argument('--full', action='store_true', help='Force full sync (ignore last sync state)')

    def handle(self, *args, **options):
        engine = HubSpotGeniusUsersSyncEngine(
            api_token=options.get('api_token'),
            batch_size=options['batch_size'],
            dry_run=options['dry_run'],
            stdout=self.stdout,
            max_records=options.get('max_records', 0),
            full=options.get('full', False)
        )
        asyncio.run(engine.run_sync())
