"""
New HubSpot deals sync command using the unified architecture
"""
from ingestion.management.commands.base_hubspot_sync import BaseHubSpotSyncCommand
from ingestion.sync.hubspot.engines import HubSpotDealSyncEngine

class Command(BaseHubSpotSyncCommand):
    """Sync deals from HubSpot using new architecture"""
    
    help = "Sync deals from HubSpot API using the new unified architecture"
    
    def get_sync_engine(self, **options):
        """Get the deal sync engine"""
        return HubSpotDealSyncEngine(
            batch_size=options.get('batch_size', 100),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "deals"
