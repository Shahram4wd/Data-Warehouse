"""
New HubSpot associations sync command using the unified architecture
"""
from ingestion.management.commands.base_hubspot_sync import BaseHubSpotSyncCommand
from ingestion.sync.hubspot.engines import HubSpotAssociationSyncEngine

class Command(BaseHubSpotSyncCommand):
    """Sync associations from HubSpot using new architecture"""
    
    help = "Sync associations between HubSpot objects using the new unified architecture"
    
    def add_arguments(self, parser):
        """Add association-specific arguments"""
        super().add_arguments(parser)
        parser.add_argument(
            "--from-object",
            type=str,
            default="contacts",
            help="Source object type (contacts, deals, appointments, etc.)"
        )
        parser.add_argument(
            "--to-object",
            type=str,
            default="deals",
            help="Target object type (contacts, deals, appointments, etc.)"
        )
    
    def get_sync_engine(self, **options):
        """Get the association sync engine"""
        return HubSpotAssociationSyncEngine(
            batch_size=options.get('batch_size', 100),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "associations"
    
    async def run_sync(self, **options):
        """Run the association sync with object type parameters"""
        # Determine last sync time
        last_sync = self.get_last_sync_time(**options)
        
        # Prepare sync parameters
        sync_params = {
            'last_sync': last_sync,
            'limit': options.get('batch_size', 100),
            'max_records': options.get('max_records', 0),
            'endpoint': self.get_sync_name(),
            'from_object_type': options.get('from_object', 'contacts'),
            'to_object_type': options.get('to_object', 'deals')
        }
        
        if options.get('debug'):
            self.stdout.write(f"Sync parameters: {sync_params}")
        
        # Run the sync
        history = await self.sync_engine.run_sync(**sync_params)
        
        return history
