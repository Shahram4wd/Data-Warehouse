"""
Django management command for syncing Genius jobs following CRM sync guide patterns.
Supports both --full and --force flags with distinct behaviors.
"""
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from ingestion.sync.genius.engines.jobs_streaming import StreamingGeniusJobsSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Genius jobs data using the standardized sync engine'

    def add_arguments(self, parser):
        """Add command arguments following CRM sync guide standards"""
        
        # Core sync options
        parser.add_argument(
            '--full',
            action='store_true',
            help='Force full sync instead of incremental (ignores last sync timestamp)'
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
            '--end-date',
            type=str,
            help='End date for date range sync (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
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
        
        # Force overwrite flag
        parser.add_argument(
            '--force',
            action='store_true',
            help='Completely replace existing records (force overwrite mode)'
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
        """Main command handler"""
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            self.stdout.write("🐛 DEBUG MODE - Verbose logging enabled")
        if options['dry_run']:
            self.stdout.write("🔍 DRY RUN MODE - No database changes will be made")
        
        # Determine sync mode and display appropriate message
        if options.get('full'):
            self.stdout.write("� FULL SYNC MODE - Ignoring last sync timestamp")
        else:
            self.stdout.write("🔧 DELTA SYNC MODE - Processing updates since last sync")
            
        if options.get('force'):
            self.stdout.write("🔄 FORCE MODE - Existing records will be completely replaced")
        
        since_date = self.parse_datetime_arg(options.get('since'))
        if options.get('full'):
            since_date = None
            
        try:
            engine = StreamingGeniusJobsSyncEngine()
            result = engine.sync_jobs(
                since_date=since_date,
                force_overwrite=options.get('force', False),
                dry_run=options.get('dry_run', False),
                max_records=options.get('max_records'),
                full_sync=options.get('full', False)
            )
            
            self.stdout.write("✅ Sync completed successfully:")
            self.stdout.write(f"   🆔 Sync ID: {result.get('sync_id', 'N/A')}")
            self.stdout.write(f"   📊 Total Processed: {result['total_processed']} records")
            self.stdout.write(f"   ➕ Created: {result['created']} records")
            self.stdout.write(f"   📝 Updated: {result['updated']} records")
            self.stdout.write(f"   ❌ Errors: {result['errors']} records")
            
        except Exception as e:
            logger.exception("Genius jobs sync failed")
            self.stdout.write(
                self.style.ERROR(f"❌ Sync failed: {str(e)}")
            )
            raise

