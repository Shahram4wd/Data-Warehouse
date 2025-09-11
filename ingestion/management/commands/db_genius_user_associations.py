"""
Django management command for Genius user associations sync
"""
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.sync.genius.engines.user_associations import GeniusUserAssociationsSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync user associations data from Genius CRM database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        parser.add_argument(
            '--force',
            action='store_true', 
            help='Force overwrite existing records (replace mode)'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Sync records modified since this datetime (YYYY-MM-DD HH:MM:SS format)'
        )
        
        parser.add_argument(
            '--max-records',
            type=int,
            help='Maximum number of records to process (for testing)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be synced without making changes'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging'
        )

    def handle(self, *args, **options):
        """Execute the sync command"""
        
        # Configure logging
        if options['debug']:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        
        # Parse date arguments
        since_date = self.parse_datetime(options.get('since'))
        
        self.stdout.write(
            self.style.SUCCESS("🔄 Starting Genius User Associations Sync")
        )
        
        # Handle --full flag (ignore since_date when full is specified)
        if options['full']:
            since_date = None
            self.stdout.write("📂 FULL SYNC MODE - Ignoring last sync timestamp (fetches ALL records)")
        
        # Display flag information
        if options['force']:
            self.stdout.write("🔄 FORCE MODE - Existing records will be completely replaced")
        
        if options['dry_run']:
            self.stdout.write("🔍 DRY RUN MODE - No database changes will be made")

        # Execute sync
        try:
            engine = GeniusUserAssociationsSyncEngine()
            
            result = engine.sync_user_associations(
                since_date=since_date,
                force_overwrite=options['force'], 
                dry_run=options['dry_run'],
                max_records=options.get('max_records')
            )
            
            # Display results
            self.stdout.write("✅ Sync completed successfully:")
            self.stdout.write(f"   🆔 Sync ID: {result.get('sync_id', 'N/A')}")
            self.stdout.write(f"   📊 Total Processed: {result.get('total_processed', 0)} records")
            self.stdout.write(f"   ➕ Created: {result.get('created', 0)} records")
            self.stdout.write(f"   📝 Updated: {result.get('updated', 0)} records")
            self.stdout.write(f"   ❌ Errors: {result.get('errors', 0)} records")
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"❌ Sync failed: {str(e)}")
            )
            if options['debug']:
                import traceback
                self.stderr.write(traceback.format_exc())
            raise CommandError(f"Sync failed: {str(e)}")

    def parse_datetime(self, date_string: Optional[str]) -> Optional[datetime]:
        """Parse datetime string in YYYY-MM-DD HH:MM:SS format"""
        if not date_string:
            return None
        
        try:
            dt = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
            return timezone.make_aware(dt, timezone.get_current_timezone())
        except ValueError:
            raise CommandError(f"Invalid datetime format: {date_string}. Use YYYY-MM-DD HH:MM:SS")
