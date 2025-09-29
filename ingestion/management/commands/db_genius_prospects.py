"""
Django management command for syncing Genius prospects following CRM sync guide patterns.
Supports all universal CRM flags: --debug, --full, --force, --dry-run, --batch-size, --max-records, --start-date, --skip-validation
"""
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from ingestion.sync.genius.engines.prospects import GeniusProspectsSyncEngine

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync prospects data from Genius CRM database using the standardized sync architecture"

    def add_arguments(self, parser):
        # Universal CRM sync flags (mandatory for all CRM systems)
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
            help='Records per batch for bulk operations'
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
            help='Manual sync start date (YYYY-MM-DD)'
        )

    def parse_datetime_arg(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string argument with timezone handling"""
        if not date_str:
            return None
            
        # Try parsing as datetime first, then as date
        try:
            parsed = parse_datetime(date_str)
            if parsed:
                # If timezone-naive, make it timezone-aware using Django's current timezone
                if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
                    parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
                return parsed
                
            # If no time component, try parsing as date and add time
            from django.utils.dateparse import parse_date
            date_obj = parse_date(date_str)
            if date_obj:
                dt = datetime.combine(date_obj, datetime.min.time())
                return timezone.make_aware(dt, timezone.get_current_timezone())
                
            raise ValueError(f"Could not parse datetime: {date_str}")
        except Exception as e:
            raise ValueError(f"Invalid datetime format '{date_str}': {e}")

    def handle(self, *args, **options):
        """Main command handler using sync engine pattern"""
        
        # Set up logging
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            self.stdout.write("🐛 DEBUG MODE - Verbose logging enabled")
        
        # Handle dry run
        if options['dry_run']:
            self.stdout.write("🔍 DRY RUN MODE - No database changes will be made")
        
        # Show flag modes
        if options.get('force'):
            self.stdout.write("🔄 FORCE MODE - Overwriting existing records")
        if options.get('full'):
            self.stdout.write("📋 FULL SYNC - Ignoring last sync timestamp")
        
        # Parse datetime arguments
        start_date = self.parse_datetime_arg(options.get('start_date'))
        
        try:
            # Initialize sync engine
            engine = GeniusProspectsSyncEngine()
            
            # Determine sync mode
            sync_mode = 'force' if options.get('force') else 'incremental'
            if options.get('full'):
                sync_mode = 'full'
            
            # Prepare sync parameters
            sync_params = {
                'sync_mode': sync_mode,
                'batch_size': options.get('batch_size', 500),
                'max_records': options.get('max_records'),
                'dry_run': options.get('dry_run', False),
                'debug': options.get('debug', False),
                'skip_validation': options.get('skip_validation', False)
            }
            
            # Add date parameters if provided
            if start_date:
                sync_params['start_date'] = start_date
            
            # Execute sync using new method signature
            stats = engine.sync_prospects(**sync_params)
            
            # Display results
            self.stdout.write("✅ Sync completed successfully:")
            self.stdout.write(f"   📊 Processed: {stats.get('total_processed', 0)} records")
            self.stdout.write(f"   ➕ Created: {stats.get('created', 0)} records")
            self.stdout.write(f"   📝 Updated: {stats.get('updated', 0)} records")
            self.stdout.write(f"   ❌ Errors: {stats.get('errors', 0)} records")
            self.stdout.write(f"   ⏭️ Skipped: {stats.get('skipped', 0)} records")
            
            if stats.get('sync_record_id'):
                self.stdout.write(f"   🆔 SyncHistory ID: {stats['sync_record_id']}")
            
        except Exception as e:
            logger.exception("Genius prospects sync failed")
            self.stdout.write(
                self.style.ERROR(f"❌ Sync failed: {str(e)}")
            )
            raise
