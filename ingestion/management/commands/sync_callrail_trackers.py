"""
Management command to sync CallRail trackers data
"""
import logging
import asyncio
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ingestion.sync.callrail.engines.trackers import TrackersSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync CallRail trackers data'
    
    def add_arguments(self, parser):
        # Standard CRM sync flags according to sync_crm_guide.md
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        parser.add_argument(
            '--force-overwrite',
            action='store_true',
            help='Completely replace existing records'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Manual sync start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test run without database writes'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Records per API batch (default: 100)'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            default=0,
            help='Limit total records (0 = unlimited)'
        )
        parser.add_argument(
            '--company-id',
            type=str,
            help='Optional company ID to filter trackers'
        )
    
    def handle(self, *args, **options):
        """Handle the management command"""
        try:
            # Check if CallRail API key is configured
            api_key = getattr(settings, 'CALLRAIL_API_KEY', None) or os.getenv('CALLRAIL_API_KEY')
            if not api_key:
                raise CommandError("CALLRAIL_API_KEY not configured in settings or environment")
            
            company_id = options.get('company_id')
            full_sync = options.get('full', False)
            force_overwrite = options.get('force_overwrite', False)
            since_date = options.get('since')
            dry_run = options.get('dry_run', False)
            batch_size = options.get('batch_size', 100)
            max_records = options.get('max_records', 0)
            
            self.stdout.write(
                self.style.SUCCESS('Starting CallRail trackers sync')
            )
            
            if company_id:
                self.stdout.write(f'Filtering by company: {company_id}')
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('DRY RUN MODE - No data will be saved')
                )
            
            if force_overwrite:
                self.stdout.write(
                    self.style.WARNING('FORCE OVERWRITE MODE - Existing records will be replaced')
                )
            
            # Run the sync
            sync_result = asyncio.run(
                self._run_sync(
                    company_id, full_sync, force_overwrite, 
                    since_date, dry_run, batch_size, max_records
                )
            )
            
            # Display results
            self._display_sync_results(sync_result)
            
        except Exception as e:
            logger.error(f"CallRail trackers sync failed: {e}")
            raise CommandError(f"Sync failed: {e}")
    
    async def _run_sync(
        self, company_id, full_sync, force_overwrite, 
        since_date, dry_run, batch_size, max_records
    ):
        """Run the actual sync process"""
        trackers_engine = TrackersSyncEngine()
        
        # Prepare sync parameters
        sync_params = {
            'full_sync': full_sync,
            'force_overwrite': force_overwrite,
            'batch_size': batch_size,
            'max_records': max_records
        }
        
        if company_id:
            sync_params['company_id'] = company_id
        
        if since_date:
            sync_params['since_date'] = since_date
        
        if dry_run:
            self.stdout.write("Dry run mode not fully implemented yet")
        
        return await trackers_engine.sync_trackers(**sync_params)
    
    def _display_sync_results(self, sync_result):
        """Display sync results in a formatted way"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("SYNC RESULTS"))
        self.stdout.write("="*50)
        
        self.stdout.write(f"Entity: trackers")
        self.stdout.write(f"Full Sync: {sync_result.get('full_sync', False)}")
        
        if 'duration' in sync_result:
            self.stdout.write(f"Duration: {sync_result['duration']:.2f} seconds")
        
        self.stdout.write("\nCounts:")
        self.stdout.write(f"  Fetched: {sync_result.get('total_fetched', 0)}")
        self.stdout.write(f"  Processed: {sync_result.get('total_processed', 0)}")
        self.stdout.write(f"  Created: {sync_result.get('total_created', 0)}")
        self.stdout.write(f"  Updated: {sync_result.get('total_updated', 0)}")
        
        error_count = len(sync_result.get('errors', []))
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
