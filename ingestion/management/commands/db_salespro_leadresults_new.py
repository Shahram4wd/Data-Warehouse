"""
Example SalesPro sync command using the new architecture
This demonstrates the new clients/engines/processors pattern
"""
import logging
import asyncio
from typing import Dict, Any
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime

# Import from the new architecture
from ingestion.sync.salespro.engines import LeadResultsSyncEngine
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Example command demonstrating new SalesPro architecture"""
    
    help = "Sync lead results using new clients/engines/processors architecture"
    
    def add_arguments(self, parser):
        """Add command arguments"""
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental"
        )
        parser.add_argument(
            "--since",
            type=str,
            help="Sync records modified since this date (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true", 
            help="Run sync without saving data to database"
        )
        parser.add_argument(
            "--max-records",
            type=int,
            default=0,
            help="Maximum number of records to sync (0 for unlimited)"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging"
        )

    def handle(self, *args, **options):
        """Handle the sync command using new architecture"""
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            
        self.stdout.write("Starting SalesPro Lead Results sync (new architecture)...")
        
        try:
            # Parse since date if provided
            since_date = None
            if options.get('since'):
                try:
                    since_date = datetime.strptime(options['since'], '%Y-%m-%d')
                    since_date = timezone.make_aware(since_date)
                    since_date = since_date.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    raise CommandError(f"Invalid date format: {options['since']}. Use YYYY-MM-DD")
            
            # Run sync using new architecture
            results = asyncio.run(self._run_sync(
                full_sync=options['full'],
                since_date=since_date,
                dry_run=options['dry_run'],
                max_records=options['max_records']
            ))
            
            # Report results
            self._report_results(results)
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.stdout.write(
                self.style.ERROR(f"❌ Lead Results sync failed: {e}")
            )
            raise CommandError(str(e))
    
    async def _run_sync(self, **kwargs) -> Dict[str, Any]:
        """Run the sync using the new engine"""
        # Create and initialize the engine
        engine = LeadResultsSyncEngine(
            batch_size=kwargs.get('batch_size', 500),
            dry_run=kwargs.get('dry_run', False)
        )
        
        # Create sync history record
        sync_history = await self._create_sync_history('leadresults')
        
        try:
            # Run the sync
            results = await engine.sync_data(**kwargs)
            
            # Update sync history on success
            await self._update_sync_history(sync_history, 'success', results)
            
            return results
            
        except Exception as e:
            # Update sync history on failure
            await self._update_sync_history(sync_history, 'failed', {'error': str(e)})
            raise
    
    async def _create_sync_history(self, sync_type: str) -> SyncHistory:
        """Create sync history record"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def create_history():
            return SyncHistory.objects.create(
                crm_source='salespro',
                sync_type=sync_type,
                start_time=timezone.now(),
                status='running'
            )
        
        return await create_history()
    
    async def _update_sync_history(self, history: SyncHistory, status: str, results: Dict[str, Any]):
        """Update sync history record"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async 
        def update_history():
            history.status = status
            history.end_time = timezone.now()
            history.records_processed = results.get('total_processed', 0)
            history.records_created = results.get('created', 0)
            history.records_updated = results.get('updated', 0)
            history.records_failed = results.get('failed', 0)
            if 'error' in results:
                history.error_message = results['error']
            history.save()
        
        await update_history()
    
    def _report_results(self, results: Dict[str, Any]):
        """Report sync results"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("SYNC RESULTS (New Architecture)")
        self.stdout.write("="*50)
        self.stdout.write(f"Total processed: {results.get('total_processed', 0)}")
        self.stdout.write(f"Created: {results.get('created', 0)}")
        self.stdout.write(f"Updated: {results.get('updated', 0)}")
        self.stdout.write(f"Failed: {results.get('failed', 0)}")
        
        if results.get('failed', 0) == 0:
            self.stdout.write(self.style.SUCCESS("🎉 Sync completed successfully!"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ Sync completed with {results.get('failed', 0)} failures"))
