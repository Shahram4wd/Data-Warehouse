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

from django.core.management.base import CommandError
from django.utils import timezone as django_timezone

from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.leadconduit.engines.base import LeadConduitSyncEngine
from ingestion.config.leadconduit_config import LeadConduitConfig

logger = logging.getLogger(__name__)


class Command(BaseSyncCommand):
    help = 'Sync all LeadConduit data (events and leads) with standardized flags'
    crm_name = 'leadconduit'
    entity_name = 'all_data'
    
    def add_arguments(self, parser):
        # Add standard BaseSyncCommand arguments
        super().add_arguments(parser)
        
        # Add backward compatibility flags with deprecation warnings
        parser.add_argument(
            '--since',
            type=str,
            help='(DEPRECATED) Use --start-date instead. Manual sync start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='(DEPRECATED) Use --force instead. Completely replace existing records'
        )
        parser.add_argument(
            '--config',
            type=str,
            default='default',
            help='Configuration profile to use'
        )
    
    def handle(self, *args, **options):
        """Handle the sync command following standardized patterns"""
        # Setup debug logging if requested
        if options.get('debug'):
            logging.getLogger().setLevel(logging.DEBUG)
            
        self.stdout.write(
            self.style.SUCCESS('Starting LeadConduit full sync...')
        )
        
        try:
            # Parse date arguments with backward compatibility
            # Priority: 1. --start-date (new standard), 2. --since (deprecated)
            since_date = None
            if options.get('start_date'):
                since_date = self.parse_date(options['start_date'])
            elif options.get('since'):  # Backward compatibility
                since_date = self.parse_date(options['since'])
                self.stdout.write(
                    self.style.WARNING('--since is deprecated, use --start-date instead')
                )
            
            end_date = self.parse_date(options.get('end_date'))
            # Handle backward compatibility for force_overwrite -> force
            force_overwrite = options.get('force', False) or options.get('force_overwrite', False)
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
            sync_engine = LeadConduitSyncEngine(config)
            
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
                raise CommandError('Sync failed')
            
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise CommandError(f'Sync failed: {e}')
    
    def run_sync(self,
                 sync_engine: LeadConduitSyncEngine,
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
        self.stdout.write(f"{sync_mode}Syncing all data{date_range}")
        
        # Run async sync
        import asyncio
        return asyncio.run(sync_engine.sync_all(
            start_date=since_date,
            end_date=end_date,
            force=force_overwrite
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
