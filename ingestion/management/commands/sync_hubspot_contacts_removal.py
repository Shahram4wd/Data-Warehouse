

import asyncio
from django.core.management.base import BaseCommand
from ingestion.sync.hubspot.engines.contacts_removal import HubSpotContactsRemovalSyncEngine

class Command(BaseCommand):
    help = "Remove local contacts that no longer exist in HubSpot (async, modular, enterprise pattern)"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Limit the number of local records to check.")
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for processing records.",
        )
        parser.add_argument(
            "--hs_contact_created_after",
            type=str,
            default=None,
            help="Only check local contacts created after this date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Only show what would be removed without actually deleting.",
        )

    def handle(self, *args, **options):
        asyncio.run(self.async_handle(**options))

    async def async_handle(self, **options):
        engine = HubSpotContactsRemovalSyncEngine(
            batch_size=options.get('batch_size', 100),
            dry_run=options.get('dry_run', False)
        )
        await engine.run_removal(
            limit=options.get('limit'),
            created_after=options.get('hs_contact_created_after'),
            dry_run=options.get('dry_run', False),
            stdout=self.stdout
        )
