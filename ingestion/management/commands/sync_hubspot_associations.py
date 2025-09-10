"""
New HubSpot associations sync command using the unified architecture
Supports both contact-appointment and contact-division associations
"""
from ingestion.management.commands.base_hubspot_sync import BaseHubSpotSyncCommand
from ingestion.sync.hubspot.engines.associations import HubSpotAssociationSyncEngine

class Command(BaseHubSpotSyncCommand):
    """Sync associations from HubSpot using new architecture
    
    Examples:
        # Standard incremental sync for contact-appointment associations
        python manage.py sync_hubspot_associations --association-type=contact_appointment
        
        # Full sync (fetch all records, but respect local timestamps)
        python manage.py sync_hubspot_associations --association-type=contact_division --full
        
        # Force overwrite ALL association records (fetch all + ignore local timestamps)
        python manage.py sync_hubspot_associations --association-type=contact_appointment --full --force
    """
    
    help = """Sync associations between HubSpot objects (contact-appointment or contact-division).
    
Use --force to completely overwrite existing association records, ignoring timestamps.
This ensures all association data is replaced with the latest from HubSpot."""
    
    def add_arguments(self, parser):
        """Add association-specific arguments"""
        super().add_arguments(parser)
        parser.add_argument(
            "--association-type",
            type=str,
            choices=["contact_appointment", "contact_division"],
            default="contact_appointment",
            help="Type of association to sync (contact_appointment or contact_division)"
        )
        # Keep legacy arguments for backward compatibility
        parser.add_argument(
            "--from-object",
            type=str,
            help="(Legacy) Source object type - use --association-type instead"
        )
        parser.add_argument(
            "--to-object",
            type=str,
            help="(Legacy) Target object type - use --association-type instead"
        )
    
    def get_sync_engine(self, **options):
        """Get the association sync engine with proper association type"""
        # Determine association type from arguments
        association_type = options.get('association_type', 'contact_appointment')
        
        # Handle legacy arguments
        from_object = options.get('from_object')
        to_object = options.get('to_object')
        
        if from_object and to_object:
            # Legacy argument mapping
            if from_object == "contacts" and to_object in ["0-421", "appointments"]:
                association_type = "contact_appointment"
            elif from_object == "contacts" and to_object in ["2-37778609", "divisions"]:
                association_type = "contact_division"
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Legacy arguments {from_object}->{to_object} not recognized. "
                        f"Using --association-type={association_type}"
                    )
                )
        
        return HubSpotAssociationSyncEngine(
            association_type=association_type,
            batch_size=options.get('batch_size', 100),
            dry_run=options.get('dry_run', False),
            force_overwrite=options.get('force_overwrite', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "associations"
    
    async def run_sync(self, **options):
        """Run the association sync with enhanced parameters"""
        # Determine last sync time
        last_sync = self.get_last_sync_time(**options)
        
        # Get association type
        association_type = options.get('association_type', 'contact_appointment')
        
        # Prepare sync parameters
        sync_params = {
            'last_sync': last_sync,
            'limit': options.get('batch_size', 100),
            'max_records': options.get('max_records', 0),
            'endpoint': f"{self.get_sync_name()}_{association_type}",
            'association_type': association_type
        }
        
        if options.get('debug'):
            self.stdout.write(f"Sync parameters: {sync_params}")
            self.stdout.write(f"Association type: {association_type}")
        
        # Run the sync
        history = await self.sync_engine.run_sync(**sync_params)
        
        return history
