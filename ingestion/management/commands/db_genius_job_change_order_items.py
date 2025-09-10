"""
Django management command for syncing Genius job change order items using the new sync engine architecture.
This command follows the CRM sync guide patterns for consistent data synchronization.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from ingestion.sync.genius.engines.job_change_order_items import GeniusJobChangeOrderItemsSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Genius job change order items data using the standardized sync engine'

    def add_arguments(self, parser):
        """Add command arguments following CRM sync guide standards"""
        
        # Core sync options
        parser.add_argument(
            '--full',
            action='store_true',
            help='Force full sync instead of incremental (ignores last sync timestamp)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without actually updating the database'
        )
        
        parser.add_argument(
            '--since',
            type=str,
            help='Sync records modified since this timestamp (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for date range sync (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for date range sync (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--max-records',
            type=int,
            help='Maximum number of records to process (for testing/debugging)'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging for detailed sync information'
        )
        
        # Additional sync options
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force overwrite existing records (delete and re-insert)'
        )

    def parse_datetime_arg(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string argument"""
        if not date_str:
            return None
            
        # Try parsing as datetime first, then as date
        try:
            parsed = parse_datetime(date_str)
            if parsed:
                return parsed
                
            # If no time component, try parsing as date and add time
            from django.utils.dateparse import parse_date
            date_obj = parse_date(date_str)
            if date_obj:
                return datetime.combine(date_obj, datetime.min.time())
                
            raise ValueError(f"Could not parse datetime: {date_str}")
        except Exception as e:
            raise ValueError(f"Invalid datetime format '{date_str}': {e}")

    def handle(self, *args, **options):
        """Main command handler"""
        
        # Set up logging
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            self.stdout.write("🐛 DEBUG MODE - Verbose logging enabled")
        
        # Handle dry run
        if options['dry_run']:
            self.stdout.write("🔍 DRY RUN MODE - No database changes will be made")
        
        # Handle force flag
        if options.get('force'):
            self.stdout.write(
                self.style.WARNING("⚠️  FORCE MODE - Existing records will be deleted and re-inserted")
            )
        
        # Parse datetime arguments
        since = self.parse_datetime_arg(options.get('since'))
        start_date = self.parse_datetime_arg(options.get('start_date'))
        end_date = self.parse_datetime_arg(options.get('end_date'))
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date cannot be after end date")
        
        # Execute sync
        try:
            result = asyncio.run(self.execute_async_sync(
                full=options.get('full', False),
                since=since,
                start_date=start_date,
                end_date=end_date,
                max_records=options.get('max_records'),
                dry_run=options.get('dry_run', False),
                debug=options.get('debug', False),
                force=options.get('force', False)
            ))
            
            # Display results
            stats = result['stats']
            self.stdout.write("✅ Sync completed successfully:")
            self.stdout.write(f"   📊 Processed: {stats['total_processed']} records")
            self.stdout.write(f"   ➕ Created: {stats['created']} records")
            self.stdout.write(f"   📝 Updated: {stats['updated']} records")
            self.stdout.write(f"   ❌ Errors: {stats['errors']} records")
            self.stdout.write(f"   ⏭️  Skipped: {stats['skipped']} records")
            self.stdout.write(f"   🆔 SyncHistory ID: {result['sync_id']}")
            
        except Exception as e:
            logger.exception("Genius job change order items sync failed")
            self.stdout.write(
                self.style.ERROR(f"❌ Sync failed: {str(e)}")
            )
            raise

    async def execute_async_sync(self, **kwargs):
        """Execute the async sync operation"""
        
        # Create sync engine
        sync_engine = GeniusJobChangeOrderItemsSyncEngine()
        
        # Create SyncHistory record at start
        sync_record = await sync_engine.create_sync_record(
            configuration={
                'command': 'db_genius_job_change_order_items',
                'full': kwargs.get('full', False),
                'force': kwargs.get('force', False),
                'since': kwargs.get('since'),
                'dry_run': kwargs.get('dry_run', False),
                'max_records': kwargs.get('max_records', 0)
            }
        )
        
        try:
            # Determine sync strategy
            sync_strategy = await sync_engine.determine_sync_strategy(
                since_param=kwargs.get('since'),
                force_overwrite=kwargs.get('force', False),
                full_sync=kwargs.get('full', False)
            )
            
            # Execute the sync
            result = await sync_engine.sync_job_change_order_items(
                since_date=sync_strategy.get('since_date'),
                force_overwrite=sync_strategy.get('force_overwrite', False),
                dry_run=kwargs.get('dry_run', False),
                max_records=kwargs.get('max_records', 0)
            )
            
            # Complete sync record with success
            await sync_engine.complete_sync_record(sync_record, result)
            
            return {'stats': result, 'sync_id': sync_record.id}
            
        except Exception as e:
            # Complete sync record with error
            await sync_engine.complete_sync_record(
                sync_record, 
                {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 1}, 
                error_message=str(e)
            )
            raise

