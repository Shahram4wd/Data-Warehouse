"""
Base sync engine for SalesRabbit following framework standards
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from django.utils import timezone
from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class SalesRabbitBaseSyncEngine(BaseSyncEngine):
    """Base sync engine for SalesRabbit following framework standards"""
    
    def __init__(self, entity_type: str, **kwargs):
        super().__init__('salesrabbit', entity_type, **kwargs)
        self.entity_type = entity_type
    
    def get_default_batch_size(self) -> int:
        """Return default batch size for SalesRabbit syncs"""
        return 500
    
    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get last successful sync timestamp - FRAMEWORK STANDARD"""
        try:
            from asgiref.sync import sync_to_async
            
            # Create an async-safe wrapper for the entire database operation
            @sync_to_async
            def get_last_sync():
                last_sync = SyncHistory.objects.filter(
                    crm_source='salesrabbit',
                    sync_type=f'{self.entity_type}_sync',
                    status='success',
                    end_time__isnull=False
                ).order_by('-end_time').first()
                
                return last_sync.end_time if last_sync else None
            
            return await get_last_sync()
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
    async def determine_sync_strategy(self, force_full: bool = False) -> Dict[str, Any]:
        """Determine sync strategy based on framework patterns"""
        last_sync = await self.get_last_sync_timestamp()
        
        strategy = {
            'type': 'full' if not last_sync or force_full else 'incremental',
            'last_sync': last_sync,
            'batch_size': self.batch_size,
            'force_full': force_full
        }
        
        logger.info(f"SalesRabbit {self.entity_type} sync strategy: {strategy['type']}")
        if strategy['type'] == 'incremental':
            logger.info(f"Last sync was at: {last_sync}")
        
        return strategy
    
    async def cleanup(self) -> None:
        """Cleanup resources after sync"""
        if hasattr(self, 'client') and self.client:
            try:
                await self.client.close()
            except Exception as e:
                logger.warning(f"Error closing client: {e}")
        
        logger.info(f"Cleaned up {self.crm_source} {self.entity_type} sync resources")
