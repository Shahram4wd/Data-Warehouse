"""
SalesRabbit users sync command using the unified architecture
"""
from ingestion.management.commands.base_salesrabbit_sync import BaseSalesRabbitSyncCommand
from ingestion.sync.salesrabbit.engines.users import SalesRabbitUserSyncEngine

class Command(BaseSalesRabbitSyncCommand):
    """Sync users from SalesRabbit using new architecture
    
    Examples:
        # Standard incremental sync
        python manage.py sync_salesrabbit_users
        
        # Full sync (fetch all records, but respect local timestamps)
        python manage.py sync_salesrabbit_users --full
        
        # Force overwrite ALL records (fetch all + ignore local timestamps)
        python manage.py sync_salesrabbit_users --full --force-overwrite
        
        # Force overwrite recent records only
        python manage.py sync_salesrabbit_users --since=2025-01-01 --force-overwrite
        
        # Resume from specific date with enhanced error logging
        python manage.py sync_salesrabbit_users --since=2025-08-25 --force-overwrite --debug
        
        # Process with smaller batches for testing
        python manage.py sync_salesrabbit_users --batch-size=50 --max-records=100 --debug
    """
    
    help = """Sync users from SalesRabbit API using the new unified architecture.
    
This command fetches user/representative data from SalesRabbit and stores it in the local database.
Users represent the sales representatives, managers, and other staff members in the SalesRabbit system.

Features:
- Delta sync using If-Modified-Since header for efficient updates
- Full sync support for complete data refresh
- Force overwrite mode for data consistency
- Batch processing with configurable batch sizes
- Comprehensive error handling and logging
- SyncHistory integration for tracking and monitoring

User data includes:
- Personal information (name, email, phone)
- Employment status and hire date
- Organization structure (department, office, team, region)
- Role and supervisor relationships
- CMS integration fields
- Profile information and external IDs
"""

    def get_sync_engine(self, **options):
        """Get the users sync engine"""
        return SalesRabbitUserSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Return the name of this sync operation"""
        return "users"
