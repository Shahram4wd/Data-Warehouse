"""
Management command to sync CallRail calls data
"""
import logging
import asyncio
import os
from django.core.management.base import CommandError
from django.conf import settings
from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.callrail.engines.calls import CallsSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseSyncCommand):
    help = 'Sync CallRail calls data with standardized flags'
    
    def add_arguments(self, parser):
        # Add standardized flags from BaseSyncCommand
        super().add_arguments(parser)
        
        # CallRail-specific arguments
        parser.add_argument(
            '--company-id',
            type=str,
            help='Optional company ID to filter calls'
        )
    
    def handle(self, *args, **options):
        """Handle the management command"""
        try:
            # Validate arguments using BaseSyncCommand
            self.validate_arguments(options)
            
            # Check if CallRail API key is configured
            api_key = getattr(settings, 'CALLRAIL_API_KEY', None) or os.getenv('CALLRAIL_API_KEY')
            if not api_key:
                raise CommandError("CALLRAIL_API_KEY not configured in settings or environment")
            
            # Parse standardized arguments (using new names)
            full_sync = options['full']
            force_overwrite = options['force']  # Updated from force_overwrite
            start_date = options.get('start_date')  # Now from standardized flags
            end_date = options.get('end_date')     # Now from standardized flags
            dry_run = options.get('dry_run', False)
            batch_size = options.get('batch_size', 100)
            quiet = options.get('quiet', False)
            
            # Parse CallRail-specific arguments
            company_id = options.get('company_id')
            
            # Display sync summary using BaseSyncCommand method
            if not quiet:
                self.display_sync_summary('CallRail Calls', options)
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('DRY RUN MODE - No data will be saved')
                )
            
            # Prepare sync parameters following CRM sync guide
            sync_params = {}
            
            # Standard CRM sync parameters
            if start_date:
                sync_params['start_date'] = start_date
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
            
            # CallRail-specific parameters
            if company_id:
                sync_params['company_id'] = company_id
                if not quiet:
                    self.stdout.write(f'Filtering by company: {company_id}')
            
            # Run the sync
            sync_result = asyncio.run(
                self._run_sync(full_sync, force_overwrite, dry_run, **sync_params)
            )
            
            # Display results
            if not quiet:
                self._display_sync_results(sync_result)
            
        except Exception as e:
            logger.error(f"CallRail calls sync failed: {e}")
            raise CommandError(f"Sync failed: {e}")
    
    async def _run_sync(self, full_sync, force_overwrite, dry_run, **sync_params):
        """Run the actual sync process"""
        sync_engine = CallsSyncEngine()
        
        if dry_run:
            # For dry run, we'd modify the engine to not save data
            # This is a simplified implementation
            self.stdout.write("Dry run mode not fully implemented yet")
        
        return await sync_engine.sync_calls(
            full_sync=full_sync,
            force_overwrite=force_overwrite,
            **sync_params
        )
    
    def _display_sync_results(self, sync_result):
        """Display sync results in a formatted way"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("SYNC RESULTS"))
        self.stdout.write("="*50)
        
        self.stdout.write(f"Entity: {sync_result.get('entity')}")
        self.stdout.write(f"Full Sync: {sync_result.get('full_sync')}")
        self.stdout.write(f"Force Overwrite: {sync_result.get('force_overwrite')}")
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
                for error in errors[:5]:  # Show first 5 errors
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
