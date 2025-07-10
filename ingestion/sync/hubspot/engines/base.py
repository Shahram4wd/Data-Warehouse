"""
Base sync engine for HubSpot entities
"""
import logging
import aiohttp
from typing import Dict, Any, Optional
from django.utils import timezone
from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.base.exceptions import SyncException

logger = logging.getLogger(__name__)

class HubSpotBaseSyncEngine(BaseSyncEngine):
    """Base sync engine for HubSpot entities with enterprise features"""
    
    def __init__(self, entity_type: str, **kwargs):
        super().__init__('hubspot', entity_type, **kwargs)
        self.client = None
        self.processor = None
        self.connection_pool = None
        self.credential_manager = None
        self.automation_engine = None
        self.alert_system = None
        
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
            self.connection_pool = connection_manager.get_pool('hubspot_api')
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
            self.automation_engine = get_automation_engine('hubspot')
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
        
    def get_default_batch_size(self) -> int:
        """Return default batch size"""
        return 100
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot client - to be implemented by subclasses"""
        # Initialize enterprise features first
        await self.initialize_enterprise_features()
        raise NotImplementedError("Subclasses must implement initialize_client")
        
    async def create_authenticated_session(self, client):
        """Create authenticated session for HubSpot client with connection pooling"""
        # Get secure credentials if available
        try:
            if self.credential_manager:
                credentials = await self.credential_manager.get_credentials('hubspot')
        except Exception:
            # Fallback if credential manager is not available
            pass
        
        # First authenticate to set up headers
        await client.authenticate()
        
        # Create session through connection pool if available
        if self.connection_pool:
            try:
                session = await self.connection_pool.get_session()
                session._default_headers = client.headers
                client.session = session
                return
            except Exception as e:
                logger.warning(f"Failed to use connection pool, falling back to regular session: {e}")
        
        # Fallback to regular session creation
        client.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=client.timeout),
            headers=client.headers
        )
        
    async def estimate_total_records(self, **kwargs) -> int:
        """Estimate total number of records for progress tracking"""
        # For HubSpot, we can make a quick count request
        # This is a simple implementation - can be enhanced per entity
        try:
            if hasattr(self.client, 'get_count'):
                return await self.client.get_count(**kwargs)
            else:
                # Default estimate based on typical HubSpot volumes
                # This can be customized per entity type
                return 1000  # Conservative estimate
        except Exception as e:
            logger.warning(f"Could not estimate total records: {e}")
            return 0
        
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.client:
                await self.client.close()
        except Exception as e:
            logger.warning(f"Error closing client: {e}")
            
        try:
            if self.connection_pool:
                await self.connection_pool.close()
        except Exception as e:
            logger.warning(f"Error closing connection pool: {e}")
            
        try:
            if self.automation_engine:
                await self.automation_engine.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up automation engine: {e}")
            
        try:
            if self.alert_system:
                await self.alert_system.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up alert system: {e}")
            
    async def handle_sync_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle sync errors with enterprise alerting"""
        logger.error(f"Sync error in {self.entity_type}: {error}")
        
        # Send alert for critical errors
        try:
            if self.alert_system:
                await self.alert_system.send_alert(
                    'sync_error',
                    f"Sync error in {self.entity_type}: {error}",
                    context=context,
                    severity='error'
                )
        except Exception as e:
            logger.warning(f"Failed to send alert: {e}")
            
        # Check for automation triggers
        try:
            if self.automation_engine:
                await self.automation_engine.handle_error(error, context)
        except Exception as e:
            logger.warning(f"Failed to handle automation: {e}")
            
    async def report_sync_metrics(self, metrics: Dict[str, Any]) -> None:
        """Report sync metrics to monitoring system"""
        # Log batch completion metrics for operational monitoring
        logger.info(f"Batch metrics - Entity: {self.entity_type}, Processed: {metrics.get('processed', 0)}, "
                   f"Success Rate: {metrics.get('success_rate', 0):.2%}")
        
        # Send performance alert if needed (but don't generate full automation reports per batch)
        try:
            if self.alert_system and metrics.get('success_rate', 0) < 0.95:
                await self.alert_system.send_alert(
                    'sync_performance',
                    f"Sync performance degraded for {self.entity_type}: {metrics.get('success_rate', 0):.2%} success rate",
                    context=metrics,
                    severity='warning'
                )
        except Exception as e:
            logger.warning(f"Failed to send performance alert: {e}")
            
        # Note: Full automation metrics reports should be generated on schedule, 
        # not per batch. See automation_engine.report_metrics() for scheduled reporting.
