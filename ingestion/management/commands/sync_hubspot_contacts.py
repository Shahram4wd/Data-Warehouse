"""
New HubSpot contacts sync command using the unified architecture
"""
from ingestion.management.commands.base_hubspot_sync import BaseHubSpotSyncCommand
from ingestion.sync.hubspot.engines.contacts import HubSpotContactSyncEngine

class Command(BaseHubSpotSyncCommand):
    """Sync contacts from HubSpot using new architecture"""
    
    help = "Sync contacts from HubSpot API using the new unified architecture"
    
    def get_sync_engine(self, **options):
        """Get the contact sync engine"""
        return HubSpotContactSyncEngine(
            batch_size=options.get('batch_size', 100),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "contacts"
