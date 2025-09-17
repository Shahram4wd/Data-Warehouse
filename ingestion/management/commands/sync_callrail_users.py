"""
Management command to sync CallRail users data
"""
import logging
import asyncio
import os
from django.core.management.base import CommandError
from django.conf import settings
from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.callrail.engines.users import UsersSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseSyncCommand):
    help = 'Sync CallRail users data with standardized flags'
    crm_name = 'callrail'
    entity_name = 'users'
    
    def add_arguments(self, parser):
        # Add standardized flags from BaseSyncCommand
        super().add_arguments(parser)
        
        # CallRail-specific arguments (none for users currently)
        pass

    def handle(self, *args, **options):
        """Handle the management command"""
        try:
            # Validate arguments using BaseSyncCommand
            self.validate_arguments(options)
            
            # Check if CallRail API key is configured
            api_key = getattr(settings, 'CALLRAIL_API_KEY', None) or os.getenv('CALLRAIL_API_KEY')
            if not api_key:
                raise CommandError("CALLRAIL_API_KEY not configured in settings or environment")
            
            # Parse standardized arguments
            full_sync = options['full']
            force_overwrite = options['force']  
            start_date = options.get('start_date')
            end_date = options.get('end_date')     
            dry_run = options.get('dry_run', False)
            batch_size = options.get('batch_size', 100)
            max_records = options.get('max_records', 0)
            quiet = options.get('quiet', False)
            
            # Display sync summary using BaseSyncCommand method
            if not quiet:
                self.stdout.write(
                    self.style.SUCCESS('Starting CallRail users sync...')
                )
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('DRY RUN MODE - No data will be saved')
                )
            
            # Prepare sync parameters following CRM sync guide
            sync_params = {}
            
            # Standard CRM sync parameters
            if start_date:
                sync_params['since_date'] = start_date  # Map to engine's expected parameter
                if not quiet:
                    self.stdout.write(f'Start date: {start_date}')
            
            if end_date:
                sync_params['end_date'] = end_date
                if not quiet:
                    self.stdout.write(f'End date: {end_date}')
            
            if batch_size != 100:
                sync_params['batch_size'] = batch_size
                if not quiet:
                    self.stdout.write(f'Batch size: {batch_size}')
            
            # Run the sync
            sync_result = asyncio.run(
                self._run_sync(full_sync, force_overwrite, dry_run, max_records, **sync_params)
            )
            
            # Display results
            self.output_results(sync_result)
            
            if not sync_result.get('success', True):
                raise CommandError('CallRail users sync failed')
            
        except Exception as e:
            logger.error(f"CallRail users sync failed: {e}")
            raise CommandError(f"Sync failed: {e}")

    async def _run_sync(self, full_sync, force_overwrite, dry_run, max_records, **sync_params):
        """Run the actual sync process"""
        # Get batch_size from sync_params if provided
        batch_size = sync_params.get('batch_size', 100)
        
        # Initialize engine with runtime flags so it can honor dry_run and batching
        sync_engine = UsersSyncEngine(dry_run=dry_run, batch_size=batch_size)
        
        if dry_run:
            # For dry run, we'd modify the engine to not save data
            # This is a simplified implementation
            self.stdout.write("Dry run mode not fully implemented yet")
        
        return await sync_engine.sync_users(
            full_sync=full_sync,
            force_overwrite=force_overwrite,
            max_records=max_records,
            **sync_params
        )
    
    def output_results(self, result):
        """Output sync results following BaseSyncCommand pattern"""
        success = result.get('success', True)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS('✓ CallRail users sync completed successfully!')
            )
        else:
            self.stdout.write(
                self.style.ERROR('✗ CallRail users sync failed')
            )
        
        # Show statistics
        total_processed = result.get('total_processed', 0)
        total_created = result.get('total_created', 0)
        total_updated = result.get('total_updated', 0)
        total_errors = result.get('total_errors', 0)
        
        self.stdout.write(f"Users: {total_processed} processed ({total_created} created, {total_updated} updated, {total_errors} failed)")
        
        # Show duration
        duration = result.get('duration', 0)
        if hasattr(duration, 'total_seconds'):
            duration = duration.total_seconds()
        self.stdout.write(f"Duration: {duration:.2f} seconds")
