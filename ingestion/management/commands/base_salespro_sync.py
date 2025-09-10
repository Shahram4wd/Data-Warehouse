"""
Base management command for SalesPro database sync operations
Following import_refactoring.md guidelines
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings
from asgiref.sync import sync_to_async
from tqdm import tqdm
from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class BaseSalesProSyncCommand(BaseCommand):
    """Base class for SalesPro database sync commands"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sync_engine = None
        
    def add_arguments(self, parser):
        """Add common arguments for all SalesPro sync commands following CRM sync guide standards"""
        # Standard CRM sync flags from the guide
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform full sync (ignore last sync timestamp)"
        )
        parser.add_argument(
            "--force", 
            action="store_true",
            help="Completely replace existing records"
        )
        parser.add_argument(
            "--since",
            type=str,
            help="Sync records modified since this date (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Test run without database writes"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Records per API batch"
        )
        parser.add_argument(
            "--max-records",
            type=int,
            default=0,
            help="Limit total records (0 = unlimited)"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable verbose logging"
        )
        parser.add_argument(
            "--no-progress",
            action="store_true",
            help="Disable progress bar display"
        )
        
    def get_sync_engine(self, **options):
        """Get the sync engine instance - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_sync_engine()")
        
    def get_sync_name(self) -> str:
        """Get the sync operation name - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_sync_name()")
        
    def handle(self, *args, **options):
        """Handle the sync command execution following CRM sync guide patterns"""
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            
        self.stdout.write(f"Starting SalesPro {self.get_sync_name()} sync...")
        
        try:
            # Get sync engine
            self.sync_engine = self.get_sync_engine(**options)
            
            # Implement delta sync logic following CRM sync guide priority order:
            # 1. --since parameter (manual override)
            # 2. --force flag (None = fetch all) 
            # 3. --full flag (None = fetch all)
            # 4. Database last sync timestamp
            # 5. Default: None (full sync)
            
            since_date = None
            sync_type = "incremental"
            
            # Priority 1: Manual override with --since
            if options.get('since'):
                try:
                    since_date = datetime.strptime(options['since'], '%Y-%m-%d')
                    since_date = timezone.make_aware(since_date)
                    sync_type = "manual_since"
                    self.stdout.write(f"Manual sync since: {since_date}")
                except ValueError:
                    raise CommandError(f"Invalid date format: {options['since']}. Use YYYY-MM-DD")
            
            # Priority 2: Force overwrite (fetch all, replace existing)
            elif options.get('force_overwrite'):
                since_date = None
                sync_type = "force_overwrite"
                self.stdout.write("Force overwrite mode: fetching all records and replacing existing")
            
            # Priority 3: Full sync flag (fetch all, respect timestamps)
            elif options.get('full'):
                since_date = None
                sync_type = "full"
                self.stdout.write("Full sync mode: fetching all records")
            
            # Priority 4 & 5: Check database for last sync timestamp or default to full
            else:
                last_sync = self._get_last_successful_sync()
                if last_sync and last_sync.end_time:
                    since_date = last_sync.end_time
                    sync_type = "incremental"
                    self.stdout.write(f"Incremental sync since: {since_date}")
                else:
                    since_date = None
                    sync_type = "full"
                    self.stdout.write("No previous sync found, performing full sync")
            
            # Log sync strategy following CRM sync guide format
            self.stdout.write(f"Sync strategy: {sync_type}")
            
            # Run sync with CRM sync guide parameters
            history = asyncio.run(self.run_sync_async(
                since_date=since_date,
                full_sync=(sync_type in ['full', 'force_overwrite']),
                force_overwrite=options.get('force_overwrite', False),
                dry_run=options['dry_run'],
                batch_size=options['batch_size'],
                max_records=options['max_records'],
                show_progress=not options['no_progress']
            ))
            
            # Report results
            self._report_results(history)
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.stdout.write(
                self.style.ERROR(f"❌ {self.get_sync_name().title()} sync failed: {e}")
            )
            raise CommandError(str(e))
            
    async def run_sync_async(self, **kwargs):
        """Run the sync operation asynchronously with enterprise features following CRM sync guide"""
        # Get sync engine
        if not self.sync_engine:
            self.sync_engine = self.get_sync_engine(**kwargs)
        
        # Pass CRM sync guide standard parameters to the engine
        sync_kwargs = {
            'since_date': kwargs.get('since_date'),
            'full_sync': kwargs.get('full_sync', False),
            'force_overwrite': kwargs.get('force_overwrite', False),
            'dry_run': kwargs.get('dry_run', False),
            'batch_size': kwargs.get('batch_size', 500),
            'max_records': kwargs.get('max_records', 0),
        }
        
        # Run sync with enterprise features
        return await self.sync_engine.run_sync(**sync_kwargs)
        
    def _get_last_successful_sync(self) -> Optional[SyncHistory]:
        """Get the last successful sync history"""
        try:
            return SyncHistory.objects.filter(
                crm_source='salespro',
                sync_type=self.get_sync_name(),
                status='success'
            ).order_by('-end_time').first()
        except Exception:
            return None
            
    def _report_results(self, history: SyncHistory):
        """Report sync results to stdout"""
        if history.status == 'success':
            self.stdout.write(
                self.style.SUCCESS(f"✅ {self.get_sync_name().title()} sync completed successfully")
            )
        elif history.status == 'partial':
            self.stdout.write(
                self.style.WARNING(f"⚠️ {self.get_sync_name().title()} sync completed with warnings")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"❌ {self.get_sync_name().title()} sync failed")
            )
            
        # Print statistics
        self.stdout.write(f"  Records processed: {history.records_processed}")
        self.stdout.write(f"  Records created: {history.records_created}")
        self.stdout.write(f"  Records updated: {history.records_updated}")
        self.stdout.write(f"  Records failed: {history.records_failed}")
        
        if history.end_time and history.start_time:
            duration = (history.end_time - history.start_time).total_seconds()
            self.stdout.write(f"  Duration: {duration:.2f} seconds")
            
            if history.records_processed > 0:
                rate = history.records_processed / duration
                self.stdout.write(f"  Rate: {rate:.2f} records/second")
