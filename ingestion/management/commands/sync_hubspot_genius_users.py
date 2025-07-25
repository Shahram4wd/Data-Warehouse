"""
Management command to sync HubSpot Genius Users
Follows import_refactoring.md enterprise architecture standards
"""
from ingestion.management.commands.base_hubspot_sync import BaseHubSpotSyncCommand
from ingestion.sync.hubspot.engines.genius_users import HubSpotGeniusUsersSyncEngine

class Command(BaseHubSpotSyncCommand):
    """Sync genius users from HubSpot using new architecture with delta sync support
    
    Examples:
        # Standard incremental sync (delta sync)
        python manage.py sync_hubspot_genius_users
        
        # Full sync (fetch all records, but respect local timestamps)
        python manage.py sync_hubspot_genius_users --full
        
        # Force overwrite ALL records (fetch all + ignore local timestamps)
        python manage.py sync_hubspot_genius_users --full --force-overwrite
        
        # Force overwrite recent records only
        python manage.py sync_hubspot_genius_users --since=2025-01-01 --force-overwrite
        
        # Limit the number of records for testing
        python manage.py sync_hubspot_genius_users --max-records=50
    """

    help = """Sync HubSpot Genius Users (custom object 2-42119425) using the new unified architecture.
    
By default, performs incremental sync (delta sync) to fetch only records modified since the last sync.
Use --force-overwrite to completely overwrite existing records, ignoring timestamps."""

    def get_sync_engine(self, **options):
        """Get the genius users sync engine"""
        return HubSpotGeniusUsersSyncEngine(
            api_token=options.get('api_token'),
            batch_size=options.get('batch_size', 100),
            dry_run=options.get('dry_run', False),
            force_overwrite=options.get('force_overwrite', False),
            max_records=options.get('max_records', 0),
            full=options.get('full', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "genius_users"

    def add_arguments(self, parser):
        """Add genius users specific arguments"""
        super().add_arguments(parser)
        parser.add_argument('--api-token', type=str, default=None, help='Override HubSpot API token')
