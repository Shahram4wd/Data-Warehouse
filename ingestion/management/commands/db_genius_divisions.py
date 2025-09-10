"""
Updated db_genius_divisions command using new sync architecture
"""
import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models.common import SyncHistory
from ingestion.sync.genius.engines.divisions import GeniusDivisionSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Download divisions using new sync architecture with SyncHistory tracking."
    
    def add_arguments(self, parser):
        # Standard CRM sync flags according to sync_crm_guide.md
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        parser.add_argument(
            '--force',
            action='store_true', 
            help='Completely replace existing records'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Manual sync start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test run without database writes'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            default=0,
            help='Limit total records (0 = unlimited)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable verbose logging'
        )

    def handle(self, *args, **options):
        """Main command handler using async sync engine"""
        
        # Set up logging level
        if options['debug']:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)
        
        # Run the async sync
        try:
            result = asyncio.run(self._run_sync(options))
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS(
                    f"Division sync completed successfully!\n"
                    f"Processed: {result['total_processed']}\n"
                    f"Created: {result['created']}\n" 
                    f"Updated: {result['updated']}\n"
                    f"Errors: {result['errors']}\n"
                    f"Skipped: {result['skipped']}"
                )
            )
            
            if result['errors'] > 0:
                self.stdout.write(
                    self.style.WARNING(f"Completed with {result['errors']} errors. Check logs for details.")
                )
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Division sync failed: {str(e)}"))
            logger.error(f"Division sync failed: {str(e)}", exc_info=True)
            raise

    async def _run_sync(self, options):
        """Run the division sync with proper configuration"""
        
        # Create sync engine
        sync_engine = GeniusDivisionSyncEngine()
        
        # Create SyncHistory record at start
        sync_record = await sync_engine.create_sync_record(
            configuration={
                'command': 'db_genius_divisions_new',
                'full': options.get('full', False),
                'force_overwrite': options.get('force_overwrite', False),
                'since': options.get('since'),
                'dry_run': options.get('dry_run', False),
                'max_records': options.get('max_records', 0)
            }
        )
        
        try:
            # Determine sync strategy
            sync_strategy = await sync_engine.determine_sync_strategy(
                since_param=options.get('since'),
                force_overwrite=options.get('force_overwrite', False),
                full_sync=options.get('full', False)
            )
            
            self.stdout.write(f"Using sync strategy: {sync_strategy['type']}")
            if sync_strategy.get('since_date'):
                self.stdout.write(f"Syncing since: {sync_strategy['since_date']}")
            
            # Execute the sync
            result = await sync_engine.sync_divisions(
                since_date=sync_strategy.get('since_date'),
                force_overwrite=sync_strategy.get('force_overwrite', False),
                dry_run=options.get('dry_run', False),
                max_records=options.get('max_records', 0)
            )
            
            # Complete sync record with success
            await sync_engine.complete_sync_record(sync_record, result)
            
            return result
            
        except Exception as e:
            # Complete sync record with error
            await sync_engine.complete_sync_record(
                sync_record, 
                {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 1}, 
                error_message=str(e)
            )
            raise
