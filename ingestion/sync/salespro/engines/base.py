"""
Base sync engine for SalesPro entities
"""
import logging
from typing import Dict, Any, Optional, List
from django.utils import timezone
from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.base.exceptions import SyncException
from ingestion.models.common import SyncHistory
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class SalesProBaseSyncEngine(BaseSyncEngine):
    """Base sync engine for SalesPro entities with enterprise features"""
    
    def __init__(self, entity_type: str, **kwargs):
        super().__init__('salespro', entity_type, **kwargs)
        self.client = None
        self.processor = None
        self.connection_pool = None
        self.credential_manager = None
        self.automation_engine = None
        self.alert_system = None
    
    @property
    def entity_type(self) -> str:
        """Get entity type (alias for sync_type for clarity)"""
        return self.sync_type
        
    async def initialize_enterprise_features(self):
        """Initialize enterprise features"""
        # Ensure connection pools are initialized
        try:
            from ingestion.base.sync_engine import ensure_connection_pools_initialized
            await ensure_connection_pools_initialized()
        except Exception as e:
            logger.warning(f"Failed to initialize connection pools: {e}")
        
        # Get connection pool from manager
        try:
            from ingestion.base.connection_pool import connection_manager
            self.connection_pool = connection_manager.get_pool('main_database')
        except Exception as e:
            logger.warning(f"Failed to get connection pool: {e}")
            self.connection_pool = None
        
        # Initialize enterprise features with fallback to mock implementations
        try:
            from ingestion.base.enterprise_compat import (
                get_credential_manager, 
                get_automation_engine, 
                get_alert_system
            )
            
            self.credential_manager = get_credential_manager()
            self.automation_engine = get_automation_engine('salespro')
            self.alert_system = get_alert_system()
            
            # Initialize if they support it
            if hasattr(self.credential_manager, 'initialize'):
                await self.credential_manager.initialize()
            if hasattr(self.automation_engine, 'initialize'):
                await self.automation_engine.initialize()
            if hasattr(self.alert_system, 'initialize'):
                await self.alert_system.initialize()
                
        except Exception as e:
            logger.warning(f"Failed to initialize enterprise features: {e}")
            self.credential_manager = None
            self.automation_engine = None
            self.alert_system = None
    
    async def get_last_sync_timestamp(self) -> Optional[str]:
        """Get last successful sync timestamp"""
        try:
            @sync_to_async
            def get_last_sync():
                last_sync = SyncHistory.objects.filter(
                    crm_source='salespro',
                    sync_type=f'{self.sync_type}',
                    status='success',
                    end_time__isnull=False
                ).order_by('-end_time').first()
                
                return last_sync.end_time.strftime('%Y-%m-%d %H:%M:%S') if last_sync else None
            
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
        
        logger.info(f"SalesPro {self.sync_type} sync strategy: {strategy['type']}")
        if strategy['type'] == 'incremental':
            logger.info(f"Last sync was at: {last_sync}")
        
        return strategy
    
    async def initialize_client(self) -> None:
        """Initialize the appropriate client for this entity"""
        # This will be overridden by specific engines
        raise NotImplementedError("Subclasses must implement initialize_client")
    
    async def initialize_processor(self) -> None:
        """Initialize the appropriate processor for this entity"""
        # This will be overridden by specific engines
        raise NotImplementedError("Subclasses must implement initialize_processor")
    
    async def sync_data(self, **kwargs) -> Dict[str, Any]:
        """Main sync method - template for all SalesPro entities"""
        await self.initialize_enterprise_features()
        await self.initialize_client()
        await self.initialize_processor()
        
        # Determine sync strategy
        strategy = await self.determine_sync_strategy(
            force_full=kwargs.get('full_sync', False)
        )
        
        # Get data from client
        since_date = None
        if strategy['type'] == 'incremental' and strategy['last_sync']:
            since_date = strategy['last_sync']
        
        if kwargs.get('since_date'):
            since_date = kwargs['since_date']
        
        # Fetch data using client
        data = await self.fetch_data(since_date=since_date, **kwargs)
        
        # Process data using processor
        results = await self.process_data(data, **kwargs)
        
        return results
    
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch data using the client"""
        raise NotImplementedError("Subclasses must implement fetch_data")
    
    async def process_data(self, data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Process data using the processor"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        return await self.processor.process_records(data, **kwargs)
