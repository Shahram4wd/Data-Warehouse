"""
Arrivy Entities Sync Command

Enterprise-grade sync command for Arrivy entities (crew members) following crm_sync_guide.md patterns.
Uses standardized SyncHistory table and modular architecture.

Usage:
    python manage.py sync_arrivy_entities
    python manage.py sync_arrivy_entities --full
    python manage.py sync_arrivy_entities --since=2025-01-01
    python manage.py sync_arrivy_entities --dry-run --batch-size=50
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.arrivy.engines.entities import ArrivyEntitiesSyncEngine

logger = logging.getLogger(__name__)

class Command(BaseSyncCommand):
    help = "Sync Arrivy entities (crew members) using enterprise CRM sync patterns"
    
    def add_arguments(self, parser):
        # Add base sync arguments (--full, --force, --since, --dry-run, --batch-size, etc.)
        super().add_arguments(parser)
        
        # Add entity-specific arguments
        parser.add_argument(
            '--crew-members-mode',
            action='store_true',
            default=True,
            help='Fetch entities as crew members from divisions (with division context)'
        )
        
        parser.add_argument(
            '--direct-entities',
            action='store_true',
            help='Fetch directly from entities endpoint instead of crew members from divisions'
        )
        
        parser.add_argument(
            '--include-inactive',
            action='store_true',
            help='Include inactive entities in sync'
        )
    
    def handle(self, *args, **options):
        """Main command handler following enterprise patterns"""
        
        try:
            # Step 1: Configure logging
            self.configure_logging(options)
            
            # Step 2: Validate arguments
            self.validate_arguments(options)
            
            self.stdout.write("Starting Arrivy entities sync...")
            
            # Create sync engine with options
            engine = ArrivyEntitiesSyncEngine(
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
                'crew_members_mode': not options.get('direct_entities', False),
                'include_inactive': options.get('include_inactive', False)
            }
            
            # Execute sync
            results = asyncio.run(engine.execute_sync(**sync_options))
            
            # Step 4: Display results using base class method
            self.display_sync_summary(results, 'entities')
            
        except Exception as e:
            # Step 5: Handle errors using base class method
            self.handle_execution_error(e, 'entities')
            raise CommandError(f"Entities sync failed: {str(e)}")

