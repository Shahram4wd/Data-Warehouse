"""
Management command to sync CallRail companies data
"""
import logging
import asyncio
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ingestion.sync.callrail.engines.companies import CompaniesSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync CallRail companies data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--full-sync',
            action='store_true',
            help='Perform full sync instead of delta sync'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving data'
        )
    
    def handle(self, *args, **options):
        """Handle the management command"""
        try:
            # Check if CallRail API key is configured
            if not hasattr(settings, 'CALLRAIL_API_KEY') or not settings.CALLRAIL_API_KEY:
                raise CommandError("CALLRAIL_API_KEY not configured in settings")
            
            full_sync = options['full_sync']
            dry_run = options.get('dry_run', False)
            
            self.stdout.write(
                self.style.SUCCESS('Starting CallRail companies sync')
            )
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('DRY RUN MODE - No data will be saved')
                )
            
            # Run the sync
            sync_result = asyncio.run(
                self._run_sync(full_sync, dry_run)
            )
            
            # Display results
            self._display_sync_results(sync_result)
            
        except Exception as e:
            logger.error(f"CallRail companies sync failed: {e}")
            raise CommandError(f"Sync failed: {e}")
    
    async def _run_sync(self, full_sync, dry_run):
        """Run the actual sync process"""
        sync_engine = CompaniesSyncEngine()
        
        if dry_run:
            self.stdout.write("Dry run mode not fully implemented yet")
        
        return await sync_engine.sync_companies(
            full_sync=full_sync
        )
    
    def _display_sync_results(self, sync_result):
        """Display sync results in a formatted way"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("SYNC RESULTS"))
        self.stdout.write("="*50)
        
        self.stdout.write(f"Account ID: {sync_result.get('account_id')}")
        self.stdout.write(f"Entity: {sync_result.get('entity')}")
        self.stdout.write(f"Full Sync: {sync_result.get('full_sync')}")
        self.stdout.write(f"Duration: {sync_result.get('duration', 0):.2f} seconds")
        
        self.stdout.write("\nCounts:")
        self.stdout.write(f"  Fetched: {sync_result.get('total_fetched', 0)}")
        self.stdout.write(f"  Processed: {sync_result.get('total_processed', 0)}")
        self.stdout.write(f"  Created: {sync_result.get('total_created', 0)}")
        self.stdout.write(f"  Updated: {sync_result.get('total_updated', 0)}")
        
        error_count = sync_result.get('total_errors', 0)
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f"  Errors: {error_count}")
            )
            
            errors = sync_result.get('errors', [])
            if errors:
                self.stdout.write("\nError Details:")
                for error in errors[:5]:
                    self.stdout.write(f"  - {error}")
                
                if len(errors) > 5:
                    self.stdout.write(f"  ... and {len(errors) - 5} more errors")
        else:
            self.stdout.write(
                self.style.SUCCESS("  Errors: 0")
            )
        
        self.stdout.write("="*50)
        
        if error_count == 0:
            self.stdout.write(
                self.style.SUCCESS("✓ Sync completed successfully!")
            )
        else:
            self.stdout.write(
                self.style.WARNING("⚠ Sync completed with errors")
            )
