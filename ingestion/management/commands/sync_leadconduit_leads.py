"""
Sync LeadConduit Leads

Django management command to sync only LeadConduit leads following
sync_crm_guide.md naming conventions.

Usage:
    python manage.py sync_leadconduit_leads
    python manage.py sync_leadconduit_leads --start-date 2024-01-01
    python manage.py sync_leadconduit_leads --force-overwrite
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from django.core.management.base import BaseCommand, CommandError

from ingestion.sync.leadconduit.engines.base import LeadConduitLeadsSyncEngine
from ingestion.config.leadconduit_config import LeadConduitConfig

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync LeadConduit leads only'
    
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
            '--debug',
            action='store_true',
            help='Enable verbose logging'
        )
        
        # LeadConduit-specific arguments (deprecated - for backward compatibility)
        parser.add_argument(
            '--start-date',
            type=str,
            help='(DEPRECATED) Use --since instead. Start date for sync (YYYY-MM-DD format, UTC)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for sync (YYYY-MM-DD format, UTC). If not provided, defaults to today'
        )
        parser.add_argument(
            '--config',
            type=str,
            default='default',
            help='Configuration profile to use'
        )
    
    def handle(self, *args, **options):
        """Handle the sync command following sync_crm_guide.md patterns"""
        # Setup debug logging if requested
        if options.get('debug'):
            logging.getLogger().setLevel(logging.DEBUG)
            
        self.stdout.write(
            self.style.SUCCESS('Starting LeadConduit leads sync...')
        )
        
        try:
            # Parse date arguments following guide priority:
            # 1. --since parameter (manual override)
            # 2. --force-overwrite flag (None = fetch all)  
            # 3. --full flag (None = fetch all)
            # 4. SyncHistory table last successful sync timestamp
            # 5. Default: None (full sync)
            
            since_date = None
            if options.get('since'):
                since_date = self.parse_date(options['since'])
            elif options.get('start_date'):  # Backward compatibility
                since_date = self.parse_date(options['start_date'])
                self.stdout.write(
                    self.style.WARNING('--start-date is deprecated, use --since instead')
                )
            
            end_date = self.parse_date(options.get('end_date'))
            force_overwrite = options.get('force_overwrite', False)
            full_sync = options.get('full', False)
            dry_run = options.get('dry_run', False)
            batch_size = options.get('batch_size', 100)
            max_records = options.get('max_records', 0)
            
            # Get configuration
            config_profile = options.get('config', 'default')
            config = LeadConduitConfig.get_config(config_profile)
            
            # Add command-line options to config
            config.update({
                'batch_size': batch_size,
                'max_records': max_records,
                'dry_run': dry_run
            })
            
            # Initialize sync engine
            sync_engine = LeadConduitLeadsSyncEngine(config)
            
            # Run sync following guide patterns
            result = self.run_sync(
                sync_engine,
                since_date=since_date,
                end_date=end_date,
                force_overwrite=force_overwrite,
                full_sync=full_sync,
                dry_run=dry_run
            )
            
            # Output results
            self.output_results(result)
            
            if not result.get('success', False):
                raise CommandError('Leads sync failed')
            
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise CommandError(f'Leads sync failed: {e}')
    
    def run_sync(self,
                 sync_engine: LeadConduitLeadsSyncEngine,
                 since_date=None,
                 end_date=None,
                 force_overwrite=False,
                 full_sync=False,
                 dry_run=False) -> Dict[str, Any]:
        """Run the sync operation following sync_crm_guide.md patterns"""
        
        # Display sync strategy
        if since_date:
            date_range = f" since {since_date.date()}"
        elif full_sync or force_overwrite:
            date_range = " (full sync)"
        else:
            date_range = " (incremental sync)"
            
        if end_date:
            date_range += f" until {end_date.date()}"
            
        sync_mode = "DRY RUN: " if dry_run else ""
        self.stdout.write(f"{sync_mode}Syncing leads{date_range}")
        
        # Run async sync
        import asyncio
        return asyncio.run(sync_engine.sync(
            since_date=since_date,
            end_date=end_date,
            force_overwrite=force_overwrite,
            full_sync=full_sync,
            dry_run=dry_run
        ))
    
    def parse_date(self, date_str: str) -> datetime:
        """Parse date string to UTC datetime"""
        if not date_str:
            return None
        
        try:
            # Parse YYYY-MM-DD format
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            # Convert to UTC timezone
            return date_obj.replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise CommandError(f'Invalid date format "{date_str}". Use YYYY-MM-DD format.')
    
    def output_results(self, result: Dict[str, Any]):
        """Output sync results"""
        if result.get('success'):
            self.stdout.write(
                self.style.SUCCESS('✓ LeadConduit leads sync completed successfully')
            )
        else:
            self.stdout.write(
                self.style.ERROR('✗ LeadConduit leads sync failed')
            )
        
        # Show details
        processed = result.get('records_processed', 0)
        created = result.get('records_created', 0)
        updated = result.get('records_updated', 0)
        failed = result.get('records_failed', 0)
        
        self.stdout.write(
            f"Leads: {processed} processed "
            f"({created} created, {updated} updated, {failed} failed)"
        )
        
        # Show timing
        if 'started_at' in result and 'completed_at' in result:
            duration = (result['completed_at'] - result['started_at']).total_seconds()
            self.stdout.write(f"Duration: {duration:.2f} seconds")
        
        # Show errors if any
        errors = result.get('errors', [])
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                self.stdout.write(
                    self.style.WARNING(f"Error: {error}")
                )
            if len(errors) > 5:
                self.stdout.write(
                    self.style.WARNING(f"... and {len(errors) - 5} more errors")
                )
        
        # Show overall error if any
        if result.get('error'):
            self.stdout.write(
                self.style.ERROR(f"Error: {result['error']}")
            )
