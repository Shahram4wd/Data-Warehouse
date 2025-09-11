"""
Django management command for syncing Genius job change order types using the new sync engine architecture.
This command follows the CRM sync guide patterns for consistent data synchronization.
"""
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from ingestion.sync.genius.clients.job_change_order_types import GeniusJobChangeOrderTypeClient
from ingestion.sync.genius.processors.job_change_order_types import GeniusJobChangeOrderTypeProcessor
from ingestion.models.genius import Genius_JobChangeOrderType
from ingestion.models import SyncHistory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Genius job change order types data using the standardized sync engine'

    def create_sync_record(self, full=False, since=None):
        """Create a SyncHistory record for tracking"""
        from django.utils import timezone
        return SyncHistory.objects.create(
            crm_source='genius',
            sync_type='job_change_order_types',
            status='running',
            start_time=timezone.now(),
            configuration={
                'full': full,
                'since': since.isoformat() if since else None,
                'command': 'db_genius_job_change_order_types'
            }
        )
    
    def complete_sync_record(self, sync_record, stats=None, status='completed', error_message=None):
        """Complete the SyncHistory record with results"""
        from django.utils import timezone
        sync_record.end_time = timezone.now()
        sync_record.status = status
        if stats:
            sync_record.records_processed = stats.get('total_processed', 0)
            sync_record.records_created = stats.get('created', 0) 
            sync_record.records_updated = stats.get('updated', 0)
            sync_record.records_failed = stats.get('errors', 0)
        if error_message:
            sync_record.error_message = error_message
        sync_record.save()
        return sync_record

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
        
        # Legacy argument support (deprecated)
        parser.add_argument(
            '--force',
            action='store_true',
            help='DEPRECATED: Use --full instead. Forces full sync ignoring timestamps.'
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
        
        # Handle legacy arguments
        if options.get('force_overwrite'):
            self.stdout.write(
                self.style.WARNING("⚠️  --force is deprecated, use --full instead")
            )
            options['full'] = True
        
        # Parse datetime arguments
        since = self.parse_datetime_arg(options.get('since'))
        start_date = self.parse_datetime_arg(options.get('start_date'))
        end_date = self.parse_datetime_arg(options.get('end_date'))
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date cannot be after end date")
        
        # Initialize sync tracking
        sync_record = None
        try:
            sync_record = self.create_sync_record(
                full=options.get('full', False),
                since=since
            )
            
            # Process data in chunks
            client = GeniusJobChangeOrderTypeClient()
            processor = GeniusJobChangeOrderTypeProcessor()
            all_stats = {
                'total_processed': 0,
                'created': 0,
                'updated': 0,
                'errors': 0,
                'skipped': 0
            }
            
            # Get data from API
            all_records = []
            for chunk in client.get_chunked_data(
                'jobchangeordertypes',
                chunk_size=100000,
                full=options.get('full', False),
                since=since,
                max_records=options.get('max_records')
            ):
                all_records.extend(chunk)
                
                # Process in batches
                if len(all_records) >= 500:
                    stats = processor.process_batch(
                        all_records,
                        dry_run=options.get('dry_run', False),
                        force=options.get('force', False)
                    )
                    
                    # Update totals
                    for key in all_stats:
                        all_stats[key] += stats.get(key, 0)
                    
                    all_records = []  # Clear for next batch
            
            # Process remaining records
            if all_records:
                stats = processor.process_batch(
                    all_records,
                    dry_run=options.get('dry_run', False),
                    force=options.get('force', False)
                )
                
                # Update totals
                for key in all_stats:
                    all_stats[key] += stats.get(key, 0)
            
            # Complete sync tracking
            if sync_record:
                sync_record = self.complete_sync_record(
                    sync_record,
                    stats=all_stats,
                    status='completed'
                )
            
            # Display results
            self.stdout.write("✅ Sync completed successfully:")
            self.stdout.write(f"   📊 Processed: {all_stats.get('total_processed', 0)} records")
            self.stdout.write(f"   ➕ Created: {all_stats.get('created', 0)} records")
            self.stdout.write(f"   📝 Updated: {all_stats.get('updated', 0)} records")
            self.stdout.write(f"   ❌ Errors: {all_stats.get('errors', 0)} records")
            self.stdout.write(f"   ⏭️ Skipped: {all_stats.get('skipped', 0)} records")
            
            if sync_record:
                self.stdout.write(f"   🆔 SyncHistory ID: {sync_record.id}")
            else:
                self.stdout.write("   🆔 SyncHistory ID: None")
            
        except Exception as e:
            if sync_record:
                self.complete_sync_record(
                    sync_record,
                    status='failed',
                    error_message=str(e)
                )
            logger.exception("Genius job change order types sync failed")
            self.stdout.write(
                self.style.ERROR(f"❌ Sync failed: {str(e)}")
            )
            raise

