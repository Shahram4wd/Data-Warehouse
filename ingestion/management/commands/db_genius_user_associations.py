"""
Django management command to sync Genius user association data from MySQL to PostgreSQL
Following enterprise architecture with sync engine, client, and processors
"""
import asyncio
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings

from ingestion.sync.genius.engines.user_associations import GeniusUserAssociationsSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Genius user association data from MySQL to PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync instead of incremental'
        )
        
        parser.add_argument(
            '--since',
            type=str,
            help='Sync records modified since this timestamp (YYYY-MM-DD HH:MM:SS format)'
        )
        
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for sync range (YYYY-MM-DD format)'
        )
        
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for sync range (YYYY-MM-DD format)'
        )
        
        parser.add_argument(
            '--max-records',
            type=int,
            help='Maximum number of records to process'
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
        since = None
        if options['since']:
            try:
                since = datetime.strptime(options['since'], '%Y-%m-%d %H:%M:%S')
                since = timezone.make_aware(since)
            except ValueError:
                raise CommandError('Invalid since format. Use YYYY-MM-DD HH:MM:SS')
        
        start_date = None
        if options['start_date']:
            try:
                start_date = datetime.strptime(options['start_date'], '%Y-%m-%d')
                start_date = timezone.make_aware(start_date)
            except ValueError:
                raise CommandError('Invalid start-date format. Use YYYY-MM-DD')
        
        end_date = None
        if options['end_date']:
            try:
                end_date = datetime.strptime(options['end_date'], '%Y-%m-%d')
                end_date = timezone.make_aware(end_date.replace(hour=23, minute=59, second=59))
            except ValueError:
                raise CommandError('Invalid end-date format. Use YYYY-MM-DD')
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise CommandError('Start date must be before end date')
        
        # Show sync configuration
        self.stdout.write(
            self.style.SUCCESS("🔄 Starting Genius User Associations Sync")
        )
        
        sync_config = {
            'Full Sync': options['full'],
            'Since': since.strftime('%Y-%m-%d %H:%M:%S') if since else 'None',
            'Start Date': start_date.strftime('%Y-%m-%d') if start_date else 'None',
            'End Date': end_date.strftime('%Y-%m-%d') if end_date else 'None',
            'Max Records': options['max_records'] or 'All',
            'Dry Run': options['dry_run'],
            'Debug Mode': options['debug']
        }
        
        for key, value in sync_config.items():
            self.stdout.write(f"  {key}: {value}")
        
        self.stdout.write("")  # Empty line
        
        # Execute sync
        try:
            result = asyncio.run(self._execute_sync(
                full=options['full'],
                since=since,
                start_date=start_date,
                end_date=end_date,
                max_records=options['max_records'],
                dry_run=options['dry_run'],
                debug=options['debug']
            ))
            
            # Display results
            stats = result.get('stats', {})
            self.stdout.write(
                self.style.SUCCESS("✅ Sync completed successfully!")
            )
            self.stdout.write(f"  Sync ID: {result.get('sync_id')}")
            self.stdout.write(f"  Strategy: {result.get('sync_strategy')}")
            self.stdout.write(f"  Processed: {stats.get('processed', 0):,}")
            self.stdout.write(f"  Created: {stats.get('created', 0):,}")
            self.stdout.write(f"  Updated: {stats.get('updated', 0):,}")
            self.stdout.write(f"  Errors: {stats.get('errors', 0):,}")
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"❌ Sync failed: {str(e)}")
            )
            if options['debug']:
                import traceback
                self.stderr.write(traceback.format_exc())
            raise CommandError(f"Sync failed: {str(e)}")

    async def _execute_sync(self, **kwargs):
        """Execute the actual sync operation"""
        engine = GeniusUserAssociationsSyncEngine()
        return await engine.execute_sync(**kwargs)
