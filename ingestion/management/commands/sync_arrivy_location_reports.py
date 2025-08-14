"""
Arrivy Location Reports Sync Command

Enterprise-grade sync command for Arrivy location tracking and GPS reports following crm_sync_guide.md patterns.
Uses standardized SyncHistory table and modular architecture.

Usage:
    python manage.py sync_arrivy_location_reports
    python manage.py sync_arrivy_location_reports --full
    python manage.py sync_arrivy_location_reports --since=2025-01-01
    python manage.py sync_arrivy_location_reports --include-gps-tracks
"""

import asyncio
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.arrivy.engines.location_reports import ArrivyLocationReportsSyncEngine

logger = logging.getLogger(__name__)

class Command(BaseSyncCommand):
    help = "Sync Arrivy location reports and GPS tracking data using enterprise CRM sync patterns"
    
    def add_arguments(self, parser):
        # Add base sync arguments (--full, --force-overwrite, --since, --dry-run, --batch-size, etc.)
        super().add_arguments(parser)
        
        # Add location reports specific arguments
        parser.add_argument(
            '--include-gps-tracks',
            action='store_true',
            help='Include detailed GPS tracking data (larger dataset)'
        )
        
        parser.add_argument(
            '--track-interval',
            type=int,
            default=300,
            help='GPS tracking interval in seconds (default: 300s/5min)'
        )
        
        parser.add_argument(
            '--location-type',
            type=str,
            choices=['checkin', 'checkout', 'track', 'all'],
            default='all',
            help='Filter by location event type'
        )
        
        parser.add_argument(
            '--entity-type',
            type=str,
            choices=['task', 'customer', 'team', 'all'],
            default='all',
            help='Filter by related entity type'
        )
        
        parser.add_argument(
            '--date-range-hours',
            type=int,
            default=24,
            help='Default time range in hours for incremental sync (default: 24h)'
        )
        
        parser.add_argument(
            '--accuracy-threshold',
            type=int,
            default=100,
            help='GPS accuracy threshold in meters (default: 100m)'
        )
    
    def handle(self, *args, **options):
        """Main command handler following enterprise patterns"""
        
        try:
            # Step 1: Configure logging
            self.configure_logging(options)
            
            # Step 2: Validate arguments
            self.validate_arguments(options)
            
            self.stdout.write("Starting Arrivy location reports sync...")
            
            # Create sync engine with options
            engine = ArrivyLocationReportsSyncEngine(
                batch_size=options.get('batch_size', 100),
                max_records=options.get('max_records', 0),
                dry_run=options.get('dry_run', False),
                force_overwrite=options.get('force_overwrite', False),
                debug=options.get('debug', False)
            )
            
            # Prepare sync options
            sync_options = {
                'force_full': options.get('full', False),
                'since_param': options.get('since'),
                'include_gps_tracks': options.get('include_gps_tracks', False),
                'track_interval': options.get('track_interval', 300),
                'location_type': options.get('location_type', 'all'),
                'entity_type': options.get('entity_type', 'all'),
                'date_range_hours': options.get('date_range_hours', 24),
                'accuracy_threshold': options.get('accuracy_threshold', 100)
            }
            
            # Execute sync
            results = asyncio.run(engine.execute_sync(**sync_options))
            
            # Step 4: Display results using base class method
            self.display_sync_summary(results, 'location_reports')
            
        except Exception as e:
            # Step 5: Handle errors using base class method
            self.handle_execution_error(e, 'location_reports')
            raise CommandError(f"Location reports sync failed: {str(e)}")

