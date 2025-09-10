"""
New HubSpot deals sync command using the unified architecture
"""
from ingestion.management.commands.base_hubspot_sync import BaseHubSpotSyncCommand
from ingestion.sync.hubspot.engines.deals import HubSpotDealSyncEngine

class Command(BaseHubSpotSyncCommand):
    """Sync deals from HubSpot using new architecture
    
    Examples:
        # Standard incremental sync
        python manage.py sync_hubspot_deals
        
        # Full sync (fetch all records, but respect local timestamps)
        python manage.py sync_hubspot_deals --full
        
        # Force overwrite ALL records (fetch all + ignore local timestamps)
        python manage.py sync_hubspot_deals --full --force
        
        # Force overwrite recent records only
        python manage.py sync_hubspot_deals --since=2025-01-01 --force
    """
    
    help = """Sync deals from HubSpot API using the new unified architecture.
    
Use --force to completely overwrite existing records, ignoring timestamps.
This ensures all data is replaced with the latest from HubSpot."""
    
    def get_sync_engine(self, **options):
        """Get the deal sync engine"""
        return HubSpotDealSyncEngine(
            batch_size=options.get('batch_size', 100),
            dry_run=options.get('dry_run', False),
            force_overwrite=options.get('force_overwrite', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "deals"
