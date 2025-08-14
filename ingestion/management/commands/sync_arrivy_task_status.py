"""
Arrivy Task Status Sync Command

Enterprise-grade sync command for Arrivy task status definitions and mappings following crm_sync_guide.md patterns.
Uses standardized SyncHistory table and modular architecture.

Usage:
    python manage.py sync_arrivy_task_status
    python manage.py sync_arrivy_task_status --full
    python manage.py sync_arrivy_task_status --include-custom-statuses
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.arrivy.engines.task_status import ArrivyTaskStatusSyncEngine

logger = logging.getLogger(__name__)

class Command(BaseSyncCommand):
    help = "Sync Arrivy task status definitions and mappings using enterprise CRM sync patterns"
    
    def add_arguments(self, parser):
        # Add base sync arguments (--full, --force-overwrite, --since, --dry-run, --batch-size, etc.)
        super().add_arguments(parser)
        
        # Add task status specific arguments
        parser.add_argument(
            '--include-custom-statuses',
            action='store_true',
            help='Include custom/company-specific task statuses'
        )
        
        parser.add_argument(
            '--include-deprecated',
            action='store_true',
            help='Include deprecated/inactive status definitions'
        )
        
        parser.add_argument(
            '--status-category',
            type=str,
            choices=['active', 'pending', 'completed', 'cancelled', 'all'],
            default='all',
            help='Filter by status category'
        )
        
        parser.add_argument(
            '--include-workflow-states',
            action='store_true',
            help='Include workflow state definitions and transitions'
        )
        
        parser.add_argument(
            '--validate-mappings',
            action='store_true',
            help='Validate status mappings against existing tasks'
        )
    
    def handle(self, *args, **options):
        """Main command handler following enterprise patterns"""
        
        try:
            # Step 1: Configure logging
            self.configure_logging(options)
            
            # Step 2: Validate arguments
            self.validate_arguments(options)
            
            self.stdout.write("Starting Arrivy task status sync...")
            
            # Create sync engine with options
            engine = ArrivyTaskStatusSyncEngine(
                batch_size=options.get('batch_size', 50),  # Smaller batches for status data
                max_records=options.get('max_records', 0),
                dry_run=options.get('dry_run', False),
                force_overwrite=options.get('force_overwrite', False),
                debug=options.get('debug', False)
            )
            
            # Prepare sync options
            sync_options = {
                'force_full': options.get('full', False),
                'since_param': options.get('since'),
                'include_custom_statuses': options.get('include_custom_statuses', False),
                'include_deprecated': options.get('include_deprecated', False),
                'status_category': options.get('status_category', 'all'),
                'include_workflow_states': options.get('include_workflow_states', False),
                'validate_mappings': options.get('validate_mappings', False)
            }
            
            # Execute sync
            results = asyncio.run(engine.execute_sync(**sync_options))
            
            # Step 4: Display results using base class method
            self.display_sync_summary(results, 'task_status')
            
        except Exception as e:
            # Step 5: Handle errors using base class method
            self.handle_execution_error(e, 'task_status')
            raise CommandError(f"Task status sync failed: {str(e)}")

