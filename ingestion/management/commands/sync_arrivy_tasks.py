"""
Arrivy Tasks Sync Command

Enterprise-grade sync command for Arrivy tasks/bookings following crm_sync_guide.md patterns.
Uses standardized SyncHistory table and modular architecture.

Usage:
    python manage.py sync_arrivy_tasks
    python manage.py sync_arrivy_tasks --full
    python manage.py sync_arrivy_tasks --since=2025-01-01
    python manage.py sync_arrivy_tasks --start-date=2025-01-01 --end-date=2025-01-31
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.arrivy.engines.tasks import ArrivyTasksSyncEngine

logger = logging.getLogger(__name__)

class Command(BaseSyncCommand):
    help = "Sync Arrivy tasks/bookings using enterprise CRM sync patterns"
    
    def add_arguments(self, parser):
        # Add base sync arguments (--full, --force-overwrite, --since, --dry-run, --batch-size, etc.)
        super().add_arguments(parser)
        
        # Add task-specific arguments
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for task filtering (YYYY-MM-DD format)'
        )
        
        parser.add_argument(
            '--end-date', 
            type=str,
            help='End date for task filtering (YYYY-MM-DD format)'
        )
        
        parser.add_argument(
            '--task-status',
            type=str,
            choices=['pending', 'in_progress', 'completed', 'cancelled'],
            help='Filter tasks by status'
        )
        
        parser.add_argument(
            '--assigned-to',
            type=str,
            help='Filter tasks assigned to specific entity ID'
        )
        
        # Performance optimization arguments
        parser.add_argument(
            '--high-performance',
            action='store_true',
            help='Enable high-performance mode with concurrent API calls (use with caution)'
        )
        
        parser.add_argument(
            '--concurrent-pages',
            type=int,
            default=3,
            help='Number of pages to fetch concurrently in high-performance mode (default: 3)'
        )
    
    def handle(self, *args, **options):
        """Main command handler following enterprise patterns"""
        
        try:
            # Step 1: Configure logging
            self.configure_logging(options)
            
            # Step 2: Validate arguments
            self.validate_arguments(options)
            
            self.stdout.write("Starting Arrivy tasks sync...")
            
            # Create sync engine with options
            engine = ArrivyTasksSyncEngine(
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
            }
            
            # Add date filters if provided
            if options.get('start_date'):
                sync_options['start_date'] = self.parse_date_parameter(options['start_date'])
            if options.get('end_date'):
                sync_options['end_date'] = self.parse_date_parameter(options['end_date'])
            
            # Add additional filters
            if options.get('task_status'):
                sync_options['task_status'] = options['task_status']
            if options.get('assigned_to'):
                sync_options['assigned_to'] = options['assigned_to']
            
            # Add performance options
            if options.get('high_performance'):
                sync_options['high_performance'] = True
                sync_options['concurrent_pages'] = options.get('concurrent_pages', 3)
                self.stdout.write(
                    self.style.WARNING(
                        f"🚀 High-performance mode enabled with {options.get('concurrent_pages', 3)} concurrent pages"
                    )
                )
            
            # Execute sync
            results = asyncio.run(engine.execute_sync(**sync_options))
            
            # Step 4: Display results using base class method
            self.display_sync_summary(results, 'tasks')
            
        except Exception as e:
            # Step 5: Handle errors using base class method
            self.handle_execution_error(e, 'tasks')
            raise CommandError(f"Tasks sync failed: {str(e)}")

