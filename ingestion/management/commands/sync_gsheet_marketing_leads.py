"""
Sync Marketing Leads from Google Sheets
"""
import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from ingestion.sync.gsheet.engines import MarketingLeadsSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Sync Marketing Source Leads from Google Sheets"""
    
    help = "Sync Marketing Source Leads from Google Sheets to database"
    
    def add_arguments(self, parser):
        """Add command arguments"""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run sync without saving data to database"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force sync even if sheet hasn't been modified"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for processing records"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging"
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress output except errors"
        )
        parser.add_argument(
            "--test-connection",
            action="store_true",
            help="Test Google Sheets API connection only"
        )
        parser.add_argument(
            "--show-summary",
            action="store_true",
            help="Show sync summary and exit"
        )
    
    def handle(self, *args, **options):
        """Execute the sync command"""
        
        # Configure logging level
        if options['debug']:
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.DEBUG)
        elif options['quiet']:
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.ERROR)
        else:
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.INFO)
        
        try:
            # Initialize sync engine
            engine = MarketingLeadsSyncEngine(
                batch_size=options['batch_size'],
                dry_run=options['dry_run'],
                force_overwrite=options['force']
            )
            
            # Test connection only
            if options['test_connection']:
                self.stdout.write("Testing Google Sheets API connection...")
                if engine.client.test_connection():
                    self.stdout.write(
                        self.style.SUCCESS("✓ Google Sheets API connection successful")
                    )
                    return
                else:
                    self.stdout.write(
                        self.style.ERROR("✗ Google Sheets API connection failed")
                    )
                    return
            
            # Show summary only
            if options['show_summary']:
                self.stdout.write("Getting sync summary...")
                summary = engine.get_sync_summary()
                self._display_summary(summary)
                return
            
            # Run the sync
            self.stdout.write("Starting Marketing Leads sync from Google Sheets...")
            self.stdout.write(f"Configuration:")
            self.stdout.write(f"  - Dry run: {options['dry_run']}")
            self.stdout.write(f"  - Force sync: {options['force']}")
            self.stdout.write(f"  - Batch size: {options['batch_size']}")
            
            # Run sync (synchronous)
            result = engine.sync_with_retry_sync(max_retries=2)
            
            # Display results
            self._display_results(result, options)
            
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nSync interrupted by user")
            )
        except Exception as e:
            logger.error(f"Sync command failed: {e}")
            self.stdout.write(
                self.style.ERROR(f"Sync failed: {e}")
            )
            raise
    
    def _display_results(self, result, options):
        """Display sync results"""
        
        status = result.get('status', 'unknown')
        
        if status == 'success':
            self.stdout.write(
                self.style.SUCCESS("✓ Marketing Leads sync completed successfully!")
            )
            
            # Show statistics
            self.stdout.write("\nSync Statistics:")
            self.stdout.write(f"  Records processed: {result.get('records_processed', 0)}")
            self.stdout.write(f"  Records created: {result.get('records_created', 0)}")
            self.stdout.write(f"  Records updated: {result.get('records_updated', 0)}")
            self.stdout.write(f"  Records failed: {result.get('records_failed', 0)}")
            
            # Show sheet info
            sheet_info = result.get('sheet_info', {})
            if sheet_info:
                self.stdout.write(f"\nSheet Information:")
                self.stdout.write(f"  Sheet: {sheet_info.get('name', 'Unknown')}")
                self.stdout.write(f"  Data rows: {sheet_info.get('estimated_data_rows', 0)}")
                self.stdout.write(f"  Headers: {sheet_info.get('header_count', 0)}")
                self.stdout.write(f"  Last modified: {sheet_info.get('last_modified', 'Unknown')}")
            
            # Show dry run notice
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING("\n⚠ DRY RUN: No data was actually saved to the database")
                )
        
        elif status == 'skipped':
            self.stdout.write(
                self.style.WARNING(f"⚠ Sync skipped: {result.get('reason', 'Unknown reason')}")
            )
        
        elif status == 'failed':
            self.stdout.write(
                self.style.ERROR(f"✗ Sync failed: {result.get('error', 'Unknown error')}")
            )
        
        else:
            self.stdout.write(
                self.style.WARNING(f"? Sync status unknown: {status}")
            )
    
    def _display_summary(self, summary):
        """Display sync summary information"""
        
        self.stdout.write("Marketing Leads Sync Summary")
        self.stdout.write("=" * 40)
        
        status = summary.get('status', 'unknown')
        
        if status == 'never_synced':
            self.stdout.write(
                self.style.WARNING("No previous sync found")
            )
            return
        
        if status == 'error':
            self.stdout.write(
                self.style.ERROR(f"Error getting summary: {summary.get('error')}")
            )
            return
        
        # Last sync info
        last_sync = summary.get('last_sync_time')
        if last_sync:
            self.stdout.write(f"Last sync: {last_sync}")
            
            duration = summary.get('last_sync_duration')
            if duration:
                self.stdout.write(f"Duration: {duration:.1f} seconds")
            
            self.stdout.write(f"Status: {status}")
        
        # Data counts
        db_count = summary.get('records_in_database', 0)
        sheet_count = summary.get('records_in_sheet', 0)
        
        self.stdout.write(f"\nData Counts:")
        self.stdout.write(f"  Database: {db_count:,} records")
        self.stdout.write(f"  Sheet: {sheet_count:,} rows")
        
        if db_count != sheet_count:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Counts don't match (difference: {abs(db_count - sheet_count)})")
            )
        
        # Last sync statistics
        stats = summary.get('last_sync_stats', {})
        if stats:
            self.stdout.write(f"\nLast Sync Results:")
            self.stdout.write(f"  Processed: {stats.get('processed', 0)}")
            self.stdout.write(f"  Created: {stats.get('created', 0)}")
            self.stdout.write(f"  Updated: {stats.get('updated', 0)}")
            self.stdout.write(f"  Failed: {stats.get('failed', 0)}")
        
        # Sheet info
        sheet_info = summary.get('sheet_info', {})
        if sheet_info:
            self.stdout.write(f"\nSheet Information:")
            self.stdout.write(f"  Name: {sheet_info.get('name', 'Unknown')}")
            self.stdout.write(f"  Headers: {sheet_info.get('header_count', 0)}")
            self.stdout.write(f"  Last modified: {sheet_info.get('last_modified', 'Unknown')}")
