"""
SalesRabbit leads sync command using the unified architecture
"""
from ingestion.management.commands.base_salesrabbit_sync import BaseSalesRabbitSyncCommand
from ingestion.sync.salesrabbit.engines.leads import SalesRabbitLeadSyncEngine

class Command(BaseSalesRabbitSyncCommand):
    """Sync leads from SalesRabbit using new architecture
    
    Examples:
        # Standard incremental sync
        python manage.py sync_salesrabbit_leads
        
        # Full sync (fetch all records, but respect local timestamps)
        python manage.py sync_salesrabbit_leads --full
        
        # Force overwrite ALL records (fetch all + ignore local timestamps)
        python manage.py sync_salesrabbit_leads --full --force
        
        # Force overwrite recent records only
        python manage.py sync_salesrabbit_leads --since=2025-01-01 --force
        
        # Resume from specific date with enhanced error logging
        python manage.py sync_salesrabbit_leads --since=2025-07-16 --force --debug
        
        # Process with smaller batches for problematic data
        python manage.py sync_salesrabbit_leads --batch-size=50 --max-records=1000 --debug
    """
    
    help = """Sync leads from SalesRabbit API using the new unified architecture.
    
Use --force to completely overwrite existing records, ignoring timestamps.
This ensures all data is replaced with the latest from SalesRabbit.

Enhanced error logging provides SalesRabbit URLs and detailed field information
for easier debugging and data cleanup."""
    
    def get_sync_engine(self, **options):
        """Get the lead sync engine"""
        return SalesRabbitLeadSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False),
            force_overwrite=options.get('force_overwrite', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "leads"
