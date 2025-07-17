"""
New HubSpot divisions sync command using the unified architecture
"""
from ingestion.management.commands.base_hubspot_sync import BaseHubSpotSyncCommand
from ingestion.sync.hubspot.engines.divisions import HubSpotDivisionSyncEngine

class Command(BaseHubSpotSyncCommand):
    """Sync divisions from HubSpot using new architecture
    
    Examples:
        # Standard incremental sync
        python manage.py sync_hubspot_divisions
        
        # Full sync (fetch all records, but respect local timestamps)
        python manage.py sync_hubspot_divisions --full
        
        # Force overwrite ALL records (fetch all + ignore local timestamps)
        python manage.py sync_hubspot_divisions --full --force-overwrite
        
        # Force overwrite recent records only
        python manage.py sync_hubspot_divisions --since=2025-01-01 --force-overwrite
    """
    
    help = """Sync divisions from HubSpot API using the new unified architecture.
    
Use --force-overwrite to completely overwrite existing records, ignoring timestamps.
This ensures all data is replaced with the latest from HubSpot."""
    
    def get_sync_engine(self, **options):
        """Get the division sync engine"""
        return HubSpotDivisionSyncEngine(
            batch_size=options.get('batch_size', 50),
            dry_run=options.get('dry_run', False),
            force_overwrite=options.get('force_overwrite', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "divisions"
