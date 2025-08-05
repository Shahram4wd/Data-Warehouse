"""
Sync LeadConduit Leads

Django management command to sync only LeadConduit leads following
sync_crm_guide.md naming conventions.

Usage:
    python manage.py sync_leadconduit_leads
    python manage.py sync_leadconduit_leads --start-date 2024-01-01
    python manage.py sync_leadconduit_leads --force
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
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for sync (YYYY-MM-DD format, UTC)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for sync (YYYY-MM-DD format, UTC). If not provided, defaults to today'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Sync data since this date (YYYY-MM-DD format, UTC) - alias for --start-date'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if recent sync exists'
        )
        parser.add_argument(
            '--config',
            type=str,
            default='default',
            help='Configuration profile to use'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Minimal output'
        )
    
    def handle(self, *args, **options):
        """Handle the sync command"""
        if not options['quiet']:
            self.stdout.write(
                self.style.SUCCESS('Starting LeadConduit leads sync...')
            )
        
        try:
            # Parse date arguments (support both --start-date and --since)
            start_date = self.parse_date(options.get('start_date') or options.get('since'))
            end_date = self.parse_date(options.get('end_date'))
            
            # Get configuration
            config_profile = options.get('config', 'default')
            config = LeadConduitConfig.get_config(config_profile)
            
            # Initialize sync engine
            sync_engine = LeadConduitLeadsSyncEngine(config)
            
            # Run sync
            result = self.run_sync(
                sync_engine,
                start_date=start_date,
                end_date=end_date,
                force=options.get('force', False),
                quiet=options.get('quiet', False)
            )
            
            # Output results
            if not options['quiet']:
                self.output_results(result)
            
            if not result.get('success', False):
                raise CommandError('Leads sync failed')
            
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise CommandError(f'Leads sync failed: {e}')
    
    def run_sync(self,
                 sync_engine: LeadConduitLeadsSyncEngine,
                 start_date=None,
                 end_date=None,
                 force=False,
                 quiet=False) -> Dict[str, Any]:
        """Run the sync operation"""
        
        if not quiet:
            date_range = ""
            if start_date:
                date_range += f" from {start_date.date()}"
            if end_date:
                date_range += f" to {end_date.date()}"
            if date_range:
                self.stdout.write(f"Syncing leads{date_range}")
            else:
                self.stdout.write("Syncing leads with default date range")
        
        # Run async sync
        import asyncio
        return asyncio.run(sync_engine.sync(
            start_date=start_date,
            end_date=end_date,
            force=force
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
