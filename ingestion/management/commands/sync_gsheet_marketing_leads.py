"""
Sync Marketing Leads from Google Sheets
"""
import asyncio
import logging
from django.core.management.base import CommandError
from django.utils import timezone

from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.gsheet.engines import MarketingLeadsSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseSyncCommand):
    """Sync Marketing Source Leads from Google Sheets"""
    
    help = "Sync Marketing Source Leads from Google Sheets to database"
    crm_name = 'gsheet'
    entity_name = 'marketing_leads'
    
    def add_arguments(self, parser):
        """Add command arguments"""
        # Add standard BaseSyncCommand arguments
        super().add_arguments(parser)
        
        # Add GSheet-specific arguments
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
        """Execute the sync command following standardized patterns"""
        
        # Setup debug logging if requested
        if options.get('debug'):
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.DEBUG)
        elif options.get('quiet'):
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.ERROR)
        else:
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.INFO)
        
        self.stdout.write(
            self.style.SUCCESS('Starting GSheet marketing leads sync...')
        )
        
        try:
            # Get standardized options
            dry_run = options.get('dry_run', False)
            force_overwrite = options.get('force', False)
            batch_size = options.get('batch_size', 500)
            max_records = options.get('max_records', 0)
            
            # Initialize sync engine
            engine = MarketingLeadsSyncEngine(
                batch_size=batch_size,
                dry_run=dry_run,
                force_overwrite=force_overwrite,
                max_records=max_records
            )
            
            # Test connection only
            if options.get('test_connection'):
                self.stdout.write("Testing Google Sheets API connection...")
                if engine.client.test_connection():
                    self.stdout.write(
                        self.style.SUCCESS("✓ Google Sheets API connection successful")
                    )
                    return
                else:
                    raise CommandError("Google Sheets API connection failed")
            
            # Show summary only
            if options.get('show_summary'):
                self.stdout.write("Getting sync summary...")
                summary = engine.get_sync_summary()
                self._display_summary(summary)
                return
            
            # Display configuration
            dry_mode = "DRY RUN: " if dry_run else ""
            self.stdout.write(f"{dry_mode}Starting Marketing Leads sync from Google Sheets...")
            self.stdout.write(f"Configuration:")
            self.stdout.write(f"  - Dry run: {dry_run}")
            self.stdout.write(f"  - Force sync: {force_overwrite}")
            self.stdout.write(f"  - Batch size: {batch_size}")
            if max_records > 0:
                self.stdout.write(f"  - Max records: {max_records}")
            
            # Run sync (synchronous)
            result = engine.sync_with_retry_sync(max_retries=2)
            
            # Display results
            self.output_results(result)
            
            if not result.get('success', result.get('status') == 'success'):
                raise CommandError('Marketing leads sync failed')
            
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nSync interrupted by user")
            )
        except Exception as e:
            logger.error(f"Sync command failed: {e}")
            if not isinstance(e, CommandError):
                raise CommandError(f'Sync failed: {e}')
    
    def output_results(self, result):
        """Output sync results following BaseSyncCommand pattern"""
        status = result.get('status', 'unknown')
        success = result.get('success', status == 'success')
        
        if success or status == 'success':
            self.stdout.write(
                self.style.SUCCESS("✓ Marketing Leads sync completed successfully!")
            )
            
            # Show statistics
            records_processed = result.get('records_processed', 0)
            records_created = result.get('records_created', 0)  
            records_updated = result.get('records_updated', 0)
            records_failed = result.get('records_failed', 0)
            
            self.stdout.write(f"Records: {records_processed} processed ({records_created} created, {records_updated} updated, {records_failed} failed)")
            
            # Show sheet info
            sheet_info = result.get('sheet_info', {})
            if sheet_info:
                self.stdout.write(f"Sheet: {sheet_info.get('name', 'Unknown')} ({sheet_info.get('estimated_data_rows', 0)} rows)")
            
            # Show duration
            duration = result.get('duration', result.get('sync_duration', 0))
            if hasattr(duration, 'total_seconds'):
                duration = duration.total_seconds()
            self.stdout.write(f"Duration: {duration:.2f} seconds")
        
        elif status == 'skipped':
            self.stdout.write(
                self.style.WARNING(f"⚠ Sync skipped: {result.get('reason', 'Unknown reason')}")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"✗ Sync failed: {result.get('error', 'Unknown error')}")
            )
    
    def _display_results(self, result, options):
        """Display sync results (deprecated - use output_results)"""
        
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
