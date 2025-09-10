"""
Arrivy Groups Sync Command

Enterprise-grade sync command for Arrivy groups/crews following crm_sync_guide.md patterns.
Uses standardized SyncHistory table and modular architecture.

Usage:
    python manage.py sync_arrivy_groups
    python manage.py sync_arrivy_groups --full
    python manage.py sync_arrivy_groups --since=2025-01-01
    python manage.py sync_arrivy_groups --include-crews
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.arrivy.engines.groups import ArrivyGroupsSyncEngine

logger = logging.getLogger(__name__)

class Command(BaseSyncCommand):
    help = "Sync Arrivy groups/crews using enterprise CRM sync patterns"
    
    def add_arguments(self, parser):
        # Add base sync arguments (--full, --force, --since, --dry-run, --batch-size, etc.)
        super().add_arguments(parser)
        
        # Add group-specific arguments
        parser.add_argument(
            '--include-crews',
            action='store_true',
            help='Also sync from crews endpoint (divisions)'
        )
        
        parser.add_argument(
            '--crews-only',
            action='store_true',
            help='Sync only from crews endpoint, skip groups'
        )
        
        parser.add_argument(
            '--include-singular-crew',
            action='store_true',
            help='Include data from singular crew endpoint'
        )
        
        parser.add_argument(
            '--group-type',
            type=str,
            choices=['division', 'team', 'department', 'all'],
            default='all',
            help='Filter groups by type'
        )
        
        parser.add_argument(
            '--include-inactive',
            action='store_true',
            help='Include inactive groups in sync'
        )
    
    def handle(self, *args, **options):
        """Main command handler following enterprise patterns"""
        
        try:
            # Step 1: Configure logging
            self.configure_logging(options)
            
            # Step 2: Validate arguments
            self.validate_arguments(options)
            
            self.stdout.write("Starting Arrivy groups sync...")
            
            # Create sync engine with options
            engine = ArrivyGroupsSyncEngine(
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
                'include_crews': options.get('include_crews', False),
                'crews_only': options.get('crews_only', False),
                'include_singular_crew': options.get('include_singular_crew', False),
                'group_type': options.get('group_type', 'all'),
                'include_inactive': options.get('include_inactive', False)
            }
            
            # Execute sync
            results = asyncio.run(engine.execute_sync(**sync_options))
            
            # Step 4: Display results using base class method
            self.display_sync_summary(results, 'groups')
            
        except Exception as e:
            # Step 5: Handle errors using base class method
            self.handle_execution_error(e, 'groups')
            raise CommandError(f"Groups sync failed: {str(e)}")

