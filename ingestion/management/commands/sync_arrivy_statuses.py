"""
Arrivy Statuses Sync Command

Enterprise-grade sync command for Arrivy statuses following crm_sync_guide.md patterns.
Uses standardized SyncHistory table and modular architecture.

Usage:
    python manage.py sync_arrivy_statuses
    python manage.py sync_arrivy_statuses --include-inactive
    python manage.py sync_arrivy_statuses --dry-run
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.arrivy.engines.status import ArrivyStatusSyncEngine

logger = logging.getLogger(__name__)

class Command(BaseSyncCommand):
    help = "Sync Arrivy statuses using enterprise patterns with SyncHistory integration"
    
    def add_arguments(self, parser):
        # Add base sync arguments (--full, --force, --since, --dry-run, --batch-size, etc.)
        super().add_arguments(parser)
        
        # Add status-specific arguments
        parser.add_argument(
            '--include-inactive',
            action='store_true',
            help='Include inactive statuses in sync'
        )
    
    def handle(self, *args, **options):
        """Main command handler following enterprise patterns"""
        
        try:
            # Step 1: Configure logging
            self.configure_logging(options)
            
            # Step 2: Validate arguments
            self.validate_arguments(options)
            
            self.stdout.write("Starting Arrivy statuses sync...")
            
            # Execute sync
            results = self._sync_statuses(options)
            self._display_results(results)
            
        except Exception as e:
            logger.exception("Error during Arrivy statuses sync")
            raise CommandError(f"Statuses sync failed: {str(e)}")
    
    def _sync_statuses(self, options):
        """Execute statuses sync using the engine"""
        
        # Create engine instance
        engine = ArrivyStatusSyncEngine(
            dry_run=options.get('dry_run', False),
            batch_size=options.get('batch_size', 100),
            max_records=options.get('max_records', 0),
            debug=options.get('debug', False),
            # Distinct semantics: --force controls overwrite behavior in the engine
            force_overwrite=options.get('force', False)
        )
        
        # Prepare sync options manually
        sync_options = {
            'force_full': options.get('full', False),
            'since_param': options.get('since'),
            'include_inactive': options.get('include_inactive', False)
        }
        
        # Execute sync
        return asyncio.run(engine.execute_sync(**sync_options))
    
    def _display_results(self, results):
        """Display sync results in a user-friendly format"""
        self.stdout.write(
            self.style.SUCCESS(f"✅ Arrivy statuses sync completed!")
        )
        
        # Display basic metrics
        processed = results.get('processed', 0)
        created = results.get('created', 0)
        updated = results.get('updated', 0)
        failed = results.get('failed', 0)
        
        self.stdout.write(f"📊 Results: {processed} processed, {created} created, {updated} updated, {failed} failed")
        
        # Display performance metrics
        duration = results.get('duration_seconds', 0)
        if duration > 0:
            rate = processed / duration
            self.stdout.write(f"⚡ Performance: {rate:.2f} records/second, {duration:.2f} seconds total")
        
        # Display status-specific metrics
        endpoint_used = results.get('endpoint_used', 'unknown')
        include_inactive = results.get('include_inactive', False)
        
        self.stdout.write(f"🔗 Endpoint: {endpoint_used}")
        self.stdout.write(f"📋 Include inactive: {include_inactive}")
        
        # Display any errors
        if failed > 0:
            self.stdout.write(
                self.style.WARNING(f"⚠️  {failed} records failed to sync")
            )
