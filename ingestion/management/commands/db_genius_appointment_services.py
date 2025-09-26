"""
Django management command for syncing Genius appointment services data.
This command follows the CRM sync guide patterns with proper flag support.
"""
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from ingestion.sync.genius.engines.appointment_services import GeniusAppointmentServicesSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Genius appointment services data with delta updates and bulk operations'

    def add_arguments(self, parser):
        """Add command arguments following CRM sync guide standards"""
        
        # Core sync options - two distinct flags
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp) - fetches ALL records'
        )
        
        parser.add_argument(
            '--force',
            action='store_true', 
            help='Completely replace existing records - enables force overwrite mode'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without actually updating the database'
        )
        
        parser.add_argument(
            '--since',
            type=str,
            help='Sync records modified since this timestamp (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for date range sync (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--max-records',
            type=int,
            help='Maximum number of records to process (for testing/debugging)'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging for detailed sync information'
        )

    def parse_datetime_arg(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string argument"""
        if not date_str:
            return None
            
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
        """Main command handler"""
        
        # Set up logging
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            self.stdout.write("🐛 DEBUG MODE - Verbose logging enabled")
        
        # Display sync mode based on flags
        full_sync = options.get('full', False)
        force_overwrite = options.get('force', False)
        
        if full_sync and force_overwrite:
            self.stdout.write("� FULL SYNC MODE + FORCE OVERWRITE MODE")
        elif full_sync:
            self.stdout.write("🔧 FULL SYNC MODE - Ignoring last sync timestamp")
        elif force_overwrite:
            self.stdout.write("🔧 FORCE OVERWRITE MODE - Replacing existing records")
        else:
            self.stdout.write("🔧 DELTA SYNC MODE - Processing updates since last sync")
        
        # Handle dry run
        if options['dry_run']:
            self.stdout.write("🔍 DRY RUN MODE - No database changes will be made")
        
        # Parse datetime arguments  
        since = self.parse_datetime_arg(options.get('since'))
        start_date = self.parse_datetime_arg(options.get('start_date'))
        
        # For delta sync, use start_date if provided, otherwise since date
        since_date = None
        if not full_sync:
            since_date = start_date or since
        
        # Execute sync
        try:
            engine = GeniusAppointmentServicesSyncEngine()
            result = engine.sync_appointment_services(
                since_date=since_date,
                force_overwrite=force_overwrite,
                dry_run=options.get('dry_run', False),
                max_records=options.get('max_records'),
                full_sync=full_sync
            )
            
            # Display results
            self.stdout.write("✅ Sync completed successfully:")
            self.stdout.write(f"   🆔 Sync ID: {result.get('sync_id', 'N/A')}")
            self.stdout.write(f"   📊 Processed: {result['total_processed']:,} records")
            self.stdout.write(f"   ➕ Created: {result['created']:,} records")  
            self.stdout.write(f"   📝 Updated: {result['updated']:,} records")
            self.stdout.write(f"   ❌ Errors: {result['errors']:,} records")
            
            if result['errors'] > 0:
                self.stdout.write(f"⚠️ Completed with {result['errors']} errors. Check logs for details.")
            
        except Exception as e:
            logger.exception("Appointment services sync failed")
            self.stdout.write(
                self.style.ERROR(f"❌ Sync failed: {str(e)}")
            )
            raise

