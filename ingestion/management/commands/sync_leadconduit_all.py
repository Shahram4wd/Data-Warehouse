"""
Sync All LeadConduit Data

Django management command to sync all LeadConduit data following
sync_crm_guide.md naming conventions and architecture.

Usage:
    python manage.py sync_leadconduit_all
    python manage.py sync_leadconduit_all --start-date 2024-01-01
    python manage.py sync_leadconduit_all --force
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone as django_timezone

from ingestion.sync.leadconduit.engines.base import LeadConduitSyncEngine
from ingestion.config.leadconduit_config import LeadConduitConfig

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync all LeadConduit data (events and leads)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for sync (YYYY-MM-DD format, UTC)'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Sync data since this date (YYYY-MM-DD format, UTC) - alias for --start-date'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for sync (YYYY-MM-DD format, UTC). If not provided, defaults to today'
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
                self.style.SUCCESS('Starting LeadConduit full sync...')
            )
        
        try:
            # Parse date arguments (support both --start-date and --since)
            start_date = self.parse_date(options.get('start_date') or options.get('since'))
            end_date = self.parse_date(options.get('end_date'))
            
            # Get configuration
            config_profile = options.get('config', 'default')
            config = LeadConduitConfig.get_config(config_profile)
            
            # Initialize sync engine
            sync_engine = LeadConduitSyncEngine(config)
            
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
                raise CommandError('Sync failed')
            
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise CommandError(f'Sync failed: {e}')
    
    def run_sync(self,
                 sync_engine: LeadConduitSyncEngine,
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
                self.stdout.write(f"Syncing{date_range}")
            else:
                self.stdout.write("Syncing with default date range")
        
        # Run async sync
        import asyncio
        return asyncio.run(sync_engine.sync_all(
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
                self.style.SUCCESS('✓ LeadConduit sync completed successfully')
            )
        else:
            self.stdout.write(
                self.style.ERROR('✗ LeadConduit sync failed')
            )
        
        # Show timing
        duration = result.get('total_duration', 0)
        self.stdout.write(f"Duration: {duration:.2f} seconds")
        
        # Show entity results
        entity_results = result.get('entity_results', {})
        for entity_type, entity_result in entity_results.items():
            status = "✓" if entity_result.get('success') else "✗"
            processed = entity_result.get('records_processed', 0)
            created = entity_result.get('records_created', 0)
            updated = entity_result.get('records_updated', 0)
            failed = entity_result.get('records_failed', 0)
            
            self.stdout.write(
                f"{status} {entity_type}: {processed} processed "
                f"({created} created, {updated} updated, {failed} failed)"
            )
            
            # Show errors if any
            errors = entity_result.get('errors', [])
            if errors:
                for error in errors[:5]:  # Show first 5 errors
                    self.stdout.write(
                        self.style.WARNING(f"  Error: {error}")
                    )
                if len(errors) > 5:
                    self.stdout.write(
                        self.style.WARNING(f"  ... and {len(errors) - 5} more errors")
                    )
        
        # Show overall error if any
        if result.get('error'):
            self.stdout.write(
                self.style.ERROR(f"Error: {result['error']}")
            )
