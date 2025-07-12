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
        """Add common arguments for all SalesPro sync commands"""
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental."
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Show debug output"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run sync without saving data to database"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of records to process in each batch"
        )
        parser.add_argument(
            "--max-records",
            type=int,
            default=0,
            help="Maximum number of records to sync (0 for unlimited)"
        )
        parser.add_argument(
            "--since",
            type=str,
            help="Sync records modified since this date (YYYY-MM-DD format)"
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
        """Handle the sync command execution"""
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            
        self.stdout.write(f"Starting SalesPro {self.get_sync_name()} sync...")
        
        try:
            # Get sync engine
            self.sync_engine = self.get_sync_engine(**options)
            
            # Parse since date if provided
            since_date = None
            if options.get('since'):
                try:
                    since_date = datetime.strptime(options['since'], '%Y-%m-%d')
                    since_date = timezone.make_aware(since_date)
                except ValueError:
                    raise CommandError(f"Invalid date format: {options['since']}. Use YYYY-MM-DD")
            
            # Determine if incremental sync
            if not options['full'] and not since_date:
                # Get last successful sync
                last_sync = self._get_last_successful_sync()
                if last_sync:
                    since_date = last_sync.end_time
                    self.stdout.write(f"Incremental sync since: {since_date}")
                else:
                    self.stdout.write("No previous sync found, performing full sync")
            
            # Run sync
            history = asyncio.run(self.run_sync_async(
                since_date=since_date,
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
        """Run the sync operation asynchronously"""
        return await self.sync_engine.run_sync(**kwargs)
        
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
