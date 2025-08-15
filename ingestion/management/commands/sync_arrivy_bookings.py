"""
Arrivy Bookings Sync Command

Enterprise-grade sync command for Arrivy bookings following crm_sync_guide.md patterns.
Uses standardized SyncHistory table and modular architecture.

Usage:
    python manage.py sync_arrivy_bookings
    python manage.py sync_arrivy_bookings --full
    python manage.py sync_arrivy_bookings --since=2025-01-01
    python manage.py sync_arrivy_bookings --start-date=2025-01-01 --end-date=2025-01-31
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.arrivy.engines.bookings import ArrivyBookingsSyncEngine

logger = logging.getLogger(__name__)

class Command(BaseSyncCommand):
    help = "Sync Arrivy bookings using enterprise CRM sync patterns"
    
    def add_arguments(self, parser):
        # Add base sync arguments (--full, --force-overwrite, --since, --dry-run, --batch-size, etc.)
        super().add_arguments(parser)
        
        # Add booking-specific arguments
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for booking filtering (YYYY-MM-DD format)'
        )
        
        parser.add_argument(
            '--end-date', 
            type=str,
            help='End date for booking filtering (YYYY-MM-DD format)'
        )
        
        parser.add_argument(
            '--booking-status',
            type=str,
            choices=['pending', 'confirmed', 'in_progress', 'completed', 'cancelled'],
            help='Filter bookings by status'
        )
        
        parser.add_argument(
            '--booking-id',
            type=str,
            help='Sync a specific booking by ID'
        )
    
    def handle(self, *args, **options):
        """Execute the sync with comprehensive error handling and logging"""
        
        # Configure logging based on verbosity
        log_level = self.get_log_level(options['verbosity'])
        logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        try:
            # Parse dates if provided
            start_date = self.parse_date(options.get('start_date')) if options.get('start_date') else None
            end_date = self.parse_date(options.get('end_date')) if options.get('end_date') else None
            
            # Initialize engine with options
            engine = ArrivyBookingsSyncEngine(
                dry_run=options.get('dry_run', False),
                batch_size=options.get('batch_size', 100),
                max_records=options.get('max_records'),
                force_overwrite=options.get('force_overwrite', False)
            )
            
            # Run appropriate sync method
            if options.get('booking_id'):
                self.stdout.write(f"Syncing specific booking: {options['booking_id']}")
                results = asyncio.run(engine.sync_booking_by_id(options['booking_id']))
            elif start_date and end_date:
                self.stdout.write(f"Syncing bookings for date range: {start_date} to {end_date}")
                results = asyncio.run(engine.sync_bookings_for_date_range(start_date, end_date))
            else:
                # Standard sync
                self.stdout.write("Starting Arrivy bookings sync...")
                
                # Determine sync mode
                if options.get('full'):
                    self.stdout.write("Running FULL sync (ignoring last sync timestamp)")
                    results = asyncio.run(engine.execute_sync(full_sync=True))
                elif options.get('since'):
                    since_date = self.parse_date(options['since'])
                    self.stdout.write(f"Running sync since: {since_date}")
                    results = asyncio.run(engine.execute_sync(since_date=since_date))
                else:
                    self.stdout.write("Running incremental sync...")
                    results = asyncio.run(engine.execute_sync())
            
            # Display results
            self.display_results(results, 'bookings')
            
            # Exit with appropriate code
            if results.get('status') == 'failed':
                raise CommandError(f"Sync failed: {results.get('error', 'Unknown error')}")
            elif results.get('total_errors', 0) > 0:
                self.stdout.write(
                    self.style.WARNING(f"Sync completed with {results['total_errors']} errors")
                )
            else:
                self.stdout.write(self.style.SUCCESS("Sync completed successfully"))
                
        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            raise CommandError(f"Sync command failed: {str(e)}")
    
    def display_results(self, results: dict, sync_type: str):
        """Display sync results in a formatted way"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"ARRIVY {sync_type.upper()} SYNC RESULTS")
        self.stdout.write("="*60)
        
        # Basic info
        self.stdout.write(f"Status: {results.get('status', 'unknown')}")
        self.stdout.write(f"Sync Type: {results.get('sync_type', sync_type)}")
        
        if results.get('dry_run'):
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes were made"))
        
        # Metrics
        if 'total_processed' in results:
            self.stdout.write(f"Total Processed: {results['total_processed']}")
            self.stdout.write(f"Created: {results.get('total_created', 0)}")
            self.stdout.write(f"Updated: {results.get('total_updated', 0)}")
            self.stdout.write(f"Errors: {results.get('total_errors', 0)}")
            self.stdout.write(f"Batches: {results.get('batch_count', 0)}")
        
        # Timing
        if 'sync_duration' in results:
            self.stdout.write(f"Duration: {results['sync_duration']:.2f} seconds")
        
        # Date range info
        if 'date_range' in results:
            self.stdout.write(f"Date Range: {results['date_range']}")
        
        # Specific booking info
        if 'booking_id' in results:
            self.stdout.write(f"Booking ID: {results['booking_id']}")
        
        # Error details
        if results.get('error'):
            self.stdout.write(self.style.ERROR(f"Error: {results['error']}"))
        
        self.stdout.write("="*60 + "\n")
