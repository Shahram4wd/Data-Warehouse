"""
Base sync engine for Genius CRM synchronization
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from django.utils import timezone
from asgiref.sync import sync_to_async

from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class GeniusBaseSyncEngine:
    """Base sync engine for all Genius CRM entities"""
    
    def __init__(self, entity_type: str):
        self.crm_source = 'genius'
        self.entity_type = entity_type
    
    @sync_to_async
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get last successful sync timestamp from SyncHistory table"""
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source=self.crm_source,
                sync_type=self.entity_type,
                status__in=['success', 'completed'],
                end_time__isnull=False
            ).order_by('-end_time').first()
            
            return last_sync.end_time if last_sync else None
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
    @sync_to_async
    def create_sync_record(self, configuration: Dict[str, Any]) -> SyncHistory:
        """Create SyncHistory record at sync start"""
        return SyncHistory.objects.create(
            crm_source=self.crm_source,
            sync_type=self.entity_type,
            status='running',
            start_time=timezone.now(),
            configuration=configuration
        )
    
    def complete_sync_record(self, sync_record: SyncHistory, stats: Dict[str, int], 
                           error_message: str = None) -> None:
        """Complete SyncHistory record with results"""
        print(f"DEBUG: Completing sync record {sync_record.id} with stats: {stats}")
        logger.info(f"Completing sync record {sync_record.id} with stats: {stats}")
        
        sync_record.end_time = timezone.now()
        sync_record.records_processed = stats.get('total_processed', 0)
        sync_record.records_created = stats.get('created', 0)
        sync_record.records_updated = stats.get('updated', 0)
        sync_record.records_failed = stats.get('errors', 0)
        
        print(f"DEBUG: Set records - processed={sync_record.records_processed}, created={sync_record.records_created}")
        
        if error_message:
            sync_record.status = 'failed'
            sync_record.error_message = error_message
        else:
            sync_record.status = 'success' if stats.get('errors', 0) == 0 else 'partial'
        
        # Calculate performance metrics
        duration = (sync_record.end_time - sync_record.start_time).total_seconds()
        total_processed = stats.get('total_processed', 0)
        success_rate = ((total_processed - stats.get('errors', 0)) / total_processed) if total_processed > 0 else 0
        
        sync_record.performance_metrics = {
            'duration_seconds': duration,
            'records_per_second': total_processed / duration if duration > 0 else 0,
            'success_rate': success_rate
        }
        
        print(f"DEBUG: About to save sync record {sync_record.id}")
        logger.info(f"Saving sync record {sync_record.id}: processed={sync_record.records_processed}, created={sync_record.records_created}")
        sync_record.save()
        print(f"DEBUG: Sync record {sync_record.id} saved successfully")
        logger.info(f"Sync record {sync_record.id} saved successfully")
    
    def parse_since_parameter(self, since_param: str) -> Optional[datetime]:
        """Parse --since parameter string to datetime"""
        if not since_param:
            return None
        
        try:
            # Support both date and datetime formats
            if len(since_param) == 10:  # YYYY-MM-DD
                return datetime.strptime(since_param, '%Y-%m-%d')
            else:  # YYYY-MM-DD HH:MM:SS
                return datetime.strptime(since_param, '%Y-%m-%d %H:%M:%S')
        except ValueError as e:
            logger.error(f"Invalid --since parameter format '{since_param}': {e}")
            raise ValueError(f"--since parameter must be in format YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
    
    async def determine_sync_strategy(self, since_param: str = None, force_overwrite: bool = False, 
                                    full_sync: bool = False) -> Dict[str, Any]:
        """Determine sync strategy based on parameters"""
        
        # Priority order from CRM sync guide:
        # 1. --since parameter (manual override)
        # 2. --force flag 
        # 3. --full flag
        # 4. SyncHistory table last successful sync timestamp
        # 5. Default: full sync
        
        if since_param:
            since_date = self.parse_since_parameter(since_param)
            return {
                'type': 'manual_since',
                'since_date': since_date,
                'force_overwrite': force_overwrite
            }
        
        if force_overwrite:
            return {
                'type': 'force_overwrite', 
                'since_date': None,
                'force_overwrite': True
            }
        
        if full_sync:
            return {
                'type': 'full',
                'since_date': None,
                'force_overwrite': False
            }
        
        # Default: incremental sync using SyncHistory
        last_sync = await self.get_last_sync_timestamp()
        return {
            'type': 'incremental' if last_sync else 'initial_full',
            'since_date': last_sync,
            'force_overwrite': False
        }

    @sync_to_async
    def _save_sync_record(self, sync_record) -> None:
        """Save sync record asynchronously"""
        sync_record.save()

    @sync_to_async
    def _complete_sync_record_async(self, sync_record, stats: Dict[str, int], 
                                   error_message: str = None) -> None:
        """Complete sync record asynchronously using the proper status logic"""
        self.complete_sync_record(sync_record, stats, error_message)
