"""
Genius Prospects Management Command

This command provides a simplified interface to the Genius prospects sync engine,
following the standardized CRM sync architecture.
"""
from django.core.management.base import BaseCommand
from ingestion.sync.genius.engines.prospects import GeniusProspectsSyncEngine
import asyncio
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync prospects data from Genius CRM database using the standardized sync architecture"

    def add_arguments(self, parser):
        # Standard CRM sync arguments following the guide
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform full sync (ignore last sync timestamp)"
        )
        parser.add_argument(
            "--force",
            action="store_true", 
            help="Completely replace existing records"
        )
        parser.add_argument(
            "--since",
            type=str,
            help="Manual sync start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"
        )
        parser.add_argument(
            "--start-date",
            type=str,
            help="Start date for sync (same as --since, for backward compatibility)"
        )
        parser.add_argument(
            "--end-date", 
            type=str,
            help="End date for sync (not implemented for database sources)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Test run without database writes"
        )
        parser.add_argument(
            "--max-records",
            type=int,
            default=0,
            help="Limit total records (0 = unlimited)"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug mode with verbose logging"
        )
        
        # Legacy arguments for backward compatibility
        parser.add_argument(
            "--table",
            type=str,
            default="prospect",
            help="Table name (legacy, now fixed to 'prospect')"
        )
        parser.add_argument(
            "--start-offset",
            type=int,
            default=0,
            help="Starting offset (legacy, use --since instead)"
        )
        parser.add_argument(
            "--page",
            type=int,
            default=1,
            help="Starting page number (legacy, use --since instead)"
        )

    def handle(self, *args, **options):
        """Execute the sync using the Genius sync engine"""
        
        # Handle backward compatibility arguments
        since_param = options.get("since") or options.get("start_date")
        
        if options.get("debug"):
            logging.getLogger().setLevel(logging.DEBUG)
            self.stdout.write(self.style.SUCCESS("🐛 DEBUG MODE - Verbose logging enabled"))
        
        if options.get("dry_run"):
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes will be made"))
        
        if options.get("end_date"):
            self.stdout.write(self.style.WARNING("⚠️ --end-date is not supported for database sources"))
        
        # Show deprecation warnings for legacy arguments
        if options.get("start_offset", 0) > 0:
            self.stdout.write(self.style.WARNING("⚠️ DEPRECATED: --start-offset is deprecated. Use --since instead."))
        
        if options.get("page", 1) > 1:
            self.stdout.write(self.style.WARNING("⚠️ DEPRECATED: --page is deprecated. Use --since instead."))
        
        # Prepare sync mode display messages
        mode_messages = []
        if options.get("full"):
            mode_messages.append("FULL SYNC MODE - Ignoring last sync timestamp")
        if options.get("force"):
            mode_messages.append("FORCE OVERWRITE MODE - Completely replacing existing records")
        if not options.get("full") and not options.get("force"):
            mode_messages.append("DELTA SYNC MODE - Processing updates since last sync")
        
        if mode_messages:
            for message in mode_messages:
                self.stdout.write(self.style.WARNING(f"🔧 {message}"))
        
        # Create sync engine and execute
        sync_engine = GeniusProspectsSyncEngine()
        
        try:
            # Run the async sync operation using correct parameter names
            result = asyncio.run(sync_engine.execute_sync(
                since=since_param,
                force=options.get("force", False),  # Fixed: use 'force', not 'force_overwrite'
                full=options.get("full", False),
                dry_run=options.get("dry_run", False),
                max_records=options.get("max_records", 0)
            ))
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Sync completed successfully:\n"
                    f"   📊 Processed: {result['total_processed']:,} records\n"
                    f"   ➕ Created: {result['created']:,} records\n"
                    f"   📝 Updated: {result['updated']:,} records\n" 
                    f"   ❌ Errors: {result['errors']:,} records\n"
                    f"   🆔 SyncHistory ID: {result['sync_history_id']}"
                )
            )
            
            if result['errors'] > 0:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Completed with {result['errors']} errors. Check logs for details.")
                )
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Sync failed: {str(e)}"))
            logger.error(f"Genius prospects sync failed: {e}", exc_info=True)
            raise
