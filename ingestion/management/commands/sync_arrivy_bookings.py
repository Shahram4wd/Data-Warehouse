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
        
        try:
            # Step 1: Configure logging
            self.configure_logging(options)
            
            # Step 2: Validate arguments  
            self.validate_arguments(options)
            
            self.stdout.write("Starting Arrivy bookings sync...")
            
            # Execute sync
            results = self._sync_bookings(options)
            self._display_results(results)
            
        except Exception as e:
            logger.exception("Error during Arrivy bookings sync")
            raise CommandError(f"Bookings sync failed: {str(e)}")
    
    def _sync_bookings(self, options):
        """Execute bookings sync using the engine"""
        
        # Parse dates if provided
        start_date = self.parse_date(options.get('start_date')) if options.get('start_date') else None
        end_date = self.parse_date(options.get('end_date')) if options.get('end_date') else None
        
        # Initialize engine with options
        engine = ArrivyBookingsSyncEngine(
            dry_run=options.get('dry_run', False),
            batch_size=options.get('batch_size', 100),
            max_records=options.get('max_records', 0),
            debug=options.get('debug', False)
        )
        
        # Prepare sync options
        sync_options = {
            'force_full': options.get('full', False),
            'since_param': options.get('since'),
            'start_date': start_date,
            'end_date': end_date,
            'booking_status': options.get('booking_status'),
            'booking_id': options.get('booking_id')
        }
        
        # Execute sync
        return asyncio.run(engine.execute_sync(**sync_options))
    
    def _display_results(self, results):
        """Display sync results in a user-friendly format"""
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Arrivy bookings sync completed!\n"
                f"📊 Results: {results.get('total_processed', 0)} processed, "
                f"{results.get('total_created', 0)} created, "
                f"{results.get('total_updated', 0)} updated, "
                f"{results.get('total_errors', 0)} failed\n"
                f"⚡ Performance: {results.get('records_per_second', 0):.2f} records/second, "
                f"{results.get('sync_duration', 0):.2f} seconds total\n"
                f"🔗 Endpoint: bookings\n"
                f"📋 Filters: {results.get('filters', 'none')}"
            )
        )
        
        if results.get('total_errors', 0) > 0:
            self.stdout.write(f"⚠️  {results['total_errors']} records failed to sync")
