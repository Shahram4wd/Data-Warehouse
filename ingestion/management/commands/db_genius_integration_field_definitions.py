"""
Django management command for syncing Genius integration field definitions using the sync engine architecture.
This command follows the CRM sync guide patterns for consistent data synchronization.
"""
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from ingestion.sync.genius.engines.integration_field_definitions import GeniusIntegrationFieldDefinitionsSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Genius integration field definitions data using the standardized sync engine'

    def add_arguments(self, parser):
        """Add command arguments following CRM sync guide standards"""
        
        # Universal CRM sync flags (required by CRM sync guide)
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable verbose logging, detailed output, and test mode'
        )
        
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        
        parser.add_argument(
            '--skip-validation',
            action='store_true',
            help='Skip data validation steps'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test run without database writes'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Records per batch (default: 500)'
        )
        
        parser.add_argument(
            '--max-records',
            type=int,
            default=0,
            help='Limit total records (0 = unlimited)'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Completely replace existing records'
        )
        
        parser.add_argument(
            '--start-date',
            type=str,
            help='Manual sync start date (YYYY-MM-DD) - Note: This table has no timestamps, always performs full sync'
        )
        
        # Legacy support (deprecated)
        parser.add_argument(
            '--since',
            type=str,
            help='Deprecated: Use --start-date instead'
        )

    def parse_datetime_arg(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string argument"""
        if not date_str:
            return None
            
        # Try parsing as datetime first, then as date
        try:
            parsed = parse_datetime(date_str)
            if parsed:
                return parsed
                
            # If no time component, try parsing as date and add time
            from django.utils.dateparse import parse_date
            date_obj = parse_date(date_str)
            if date_obj:
                return datetime.combine(date_obj, datetime.min.time())
                
            raise ValueError(f"Could not parse datetime: {date_str}")
        except Exception as e:
            raise ValueError(f"Invalid datetime format '{date_str}': {e}")

    def handle(self, *args, **options):
        """Main command handler using sync engine pattern"""
        
        # Set up logging
        log_level = logging.DEBUG if options['debug'] else logging.INFO
        logging.getLogger('ingestion.sync.genius').setLevel(log_level)
        
        # Handle deprecated --since parameter
        start_date = options.get('start_date') or options.get('since')
        if options.get('since'):
            self.style.WARNING("⚠️  --since is deprecated, use --start-date instead")
        
        # Note about this table
        if start_date:
            self.stdout.write(self.style.WARNING("⚠️  Note: Integration field definitions have no timestamps - --start-date and --since parameters are ignored. Always performs full sync."))
        
        # Initialize sync engine
        engine = GeniusIntegrationFieldDefinitionsSyncEngine()
        
        # Display configuration
        self.stdout.write(self.style.SUCCESS("🚀 Starting Genius Integration Field Definitions Sync"))
        self.stdout.write(f"   ⚠️  Note: This table has no timestamps - always performing full sync")
        self.stdout.write(f"   🔄 Force overwrite: {options['force']}")
        self.stdout.write(f"   🧪 Dry run: {options['dry_run']}")
        self.stdout.write(f"   📊 Max records: {options['max_records'] or 'unlimited'}")
        self.stdout.write(f"   📦 Batch size: {options['batch_size']}")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("🧪 DRY RUN MODE: No changes will be made"))
        
        try:
            # Execute sync (always full sync for this table)
            result = engine.sync_integration_field_definitions(
                since_date=None,  # Always None for this table
                force_overwrite=options['force'],
                dry_run=options['dry_run'],
                max_records=options['max_records'],
                full_sync=True  # Always true for this table
            )
            
            # Display results
            self.stdout.write(self.style.SUCCESS("✅ Integration Field Definitions sync completed successfully!"))
            self.stdout.write(f"   📊 Total processed: {result['total_processed']:,}")
            self.stdout.write(f"   ➕ Created: {result['created']:,}")
            self.stdout.write(f"   🔄 Updated: {result['updated']:,}")
            self.stdout.write(f"   ❌ Errors: {result['errors']:,}")
            self.stdout.write(f"   ⏭️  Skipped: {result['skipped']:,}")
            
            if result['errors'] > 0:
                self.stdout.write(self.style.WARNING(f"⚠️  {result['errors']} errors occurred during sync"))
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Integration Field Definitions sync failed: {str(e)}"))
            if options['debug']:
                import traceback
                self.stderr.write(traceback.format_exc())
            raise