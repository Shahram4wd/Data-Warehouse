"""
New HubSpot divisions sync command using the unified architecture
"""
from ingestion.management.commands.base_hubspot_sync import BaseHubSpotSyncCommand
from ingestion.sync.hubspot.engines.divisions import HubSpotDivisionSyncEngine

class Command(BaseHubSpotSyncCommand):
    """Sync divisions from HubSpot using new architecture"""
    
    help = "Sync divisions from HubSpot API using the new unified architecture"
    
    def get_sync_engine(self, **options):
        """Get the division sync engine"""
        return HubSpotDivisionSyncEngine(
            batch_size=options.get('batch_size', 50),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "divisions"
