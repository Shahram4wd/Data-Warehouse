"""
New HubSpot appointments sync command using the unified architecture
"""
from ingestion.management.commands.base_hubspot_sync import BaseHubSpotSyncCommand
from ingestion.sync.hubspot.engines import HubSpotAppointmentSyncEngine

class Command(BaseHubSpotSyncCommand):
    """Sync appointments from HubSpot using new architecture"""
    
    help = "Sync appointments from HubSpot API using the new unified architecture"
    
    def get_sync_engine(self, **options):
        """Get the appointment sync engine"""
        return HubSpotAppointmentSyncEngine(
            batch_size=options.get('batch_size', 100),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "appointments"
