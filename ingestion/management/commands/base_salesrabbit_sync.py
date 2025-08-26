"""
Base management command for SalesRabbit sync operations using new architecture
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

class BaseSalesRabbitSyncCommand(BaseCommand):
    """Base class for SalesRabbit sync commands"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sync_engine = None
        
    def add_arguments(self, parser):
        """Add common arguments for all sync commands"""
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental."
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable verbose logging, detailed output, and test mode"
        )
        parser.add_argument(
            "--skip-validation",
            action="store_true",
            help="Skip data validation steps"
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
            help="Maximum number of records to process (0 for unlimited)"
        )
        parser.add_argument(
            "--start-date",
            type=str,
            help="Manual sync start date (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Completely replace existing records"
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress non-error output"
        )
        parser.add_argument(
            "--no-progress",
            action="store_true",
            help="Disable progress bar display"
        )

    def handle(self, *args, **options):
        """Main command handler"""
        # Set logging level
        if options.get("debug"):
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Validate settings - check for SalesRabbit API credentials
        if not getattr(settings, 'SALESRABBIT_API_TOKEN', None):
            raise CommandError("SALESRABBIT_API_TOKEN is not set in settings or environment variables.")
        
        if not getattr(settings, 'SALESRABBIT_API_URL', None):
            raise CommandError("SALESRABBIT_API_URL is not set in settings or environment variables.")
        
        # Initialize sync engine
        self.sync_engine = self.get_sync_engine(**options)
        
        # Run the sync
        try:
            if options.get('force'):
                self.stdout.write(self.style.WARNING(
                    f"⚠️  FORCE MODE: Starting {self.get_sync_name()} sync with complete record replacement..."
                ))
                self.stdout.write(self.style.WARNING(
                    "This will overwrite ALL existing records, ignoring timestamps and sync history."
                ))
            else:
                self.stdout.write(self.style.SUCCESS(f"Starting {self.get_sync_name()} sync..."))
            
            history = asyncio.run(self.run_sync(**options))
            
            # Report results
            self.report_results(history)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Sync failed: {str(e)}'))
            logger.error(f"SalesRabbit {self.get_sync_name()} sync failed: {str(e)}")
            raise
    
    def get_sync_engine(self, **options) -> BaseSyncEngine:
        """Get the appropriate sync engine - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_sync_engine")
    
    def get_sync_name(self) -> str:
        """Get the name of the sync operation - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_sync_name")
    
    async def run_sync(self, **options):
        """Run the sync operation"""
        # Determine last sync time
        last_sync = await self.get_last_sync_time_async(**options)
        
        # Prepare sync parameters
        sync_params = {
            'last_sync': last_sync,
            'limit': options.get('batch_size', 500),
            'max_records': options.get('max_records', 0),
            'endpoint': self.get_sync_name(),
            'show_progress': not options.get('no_progress', False),
            'force_overwrite': options.get('force', False)
        }
        
        if options.get('debug'):
            self.stdout.write(f"Sync parameters: {sync_params}")
        
        # Run the sync
        history = await self.sync_engine.run_sync(**sync_params)
        
        return history
    
    async def get_last_sync_time_async(self, **options) -> Optional[datetime]:
        """Determine the last sync time (async version)"""
        # Priority: 1) --start-date parameter, 2) --force flag, 3) --full flag, 4) database last sync
        if options.get('start_date'):
            try:
                last_sync = datetime.strptime(options['start_date'], "%Y-%m-%d")
                last_sync = timezone.make_aware(last_sync)
                if options.get('force'):
                    self.stdout.write(f"Force mode with date filter - fetching records modified since {options['start_date']}")
                else:
                    self.stdout.write(f"Using provided start date: {options['start_date']}")
                return last_sync
            except ValueError:
                raise CommandError(f"Invalid date format for --start-date. Use YYYY-MM-DD format.")
                
        if options.get('force'):
            self.stdout.write("Force mode - fetching ALL records and ignoring local timestamps")
            return None
        
        if options.get('full'):
            self.stdout.write("Performing full sync")
            return None
        
        # Get last successful sync from database using async database access
        try:
            # Convert Django ORM query to async
            @sync_to_async
            def get_last_sync_record():
                return SyncHistory.objects.filter(
                    crm_source='salesrabbit',
                    sync_type=self.get_sync_name(),
                    status='success'
                ).order_by('-end_time').first()
            
            last_sync_record = await get_last_sync_record()
            
            if last_sync_record:
                self.stdout.write(f"Performing incremental sync since {last_sync_record.end_time}")
                return last_sync_record.end_time
            else:
                self.stdout.write("No previous sync found, performing full sync")
                return None
                
        except Exception as e:
            logger.warning(f"Error getting last sync time: {e}")
            self.stdout.write("Error getting last sync time, performing full sync")
            return None
    
    def report_results(self, history: SyncHistory):
        """Report sync results to user"""
        if history.status == 'success':
            if hasattr(self.sync_engine, 'force_overwrite') and self.sync_engine.force_overwrite:
                self.stdout.write(self.style.SUCCESS(
                    f"✓ {self.get_sync_name().title()} FORCE MODE completed successfully"
                ))
                self.stdout.write(self.style.WARNING(
                    "All records were completely replaced with SalesRabbit data"
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"✓ {self.get_sync_name().title()} sync completed successfully"
                ))
        else:
            self.stdout.write(self.style.ERROR(
                f"✗ {self.get_sync_name().title()} sync failed"
            ))
        
        # Show metrics
        self.stdout.write(f"  Records processed: {history.records_processed}")
        self.stdout.write(f"  Records created: {history.records_created}")
        self.stdout.write(f"  Records updated: {history.records_updated}")
        self.stdout.write(f"  Records failed: {history.records_failed}")
        
        if history.performance_metrics:
            duration = history.performance_metrics.get('duration_seconds', 0)
            rate = history.performance_metrics.get('records_per_second', 0)
            self.stdout.write(f"  Duration: {duration:.2f} seconds")
            self.stdout.write(f"  Rate: {rate:.2f} records/second")
        
        if history.error_message:
            self.stdout.write(self.style.ERROR(f"  Error: {history.error_message}"))
