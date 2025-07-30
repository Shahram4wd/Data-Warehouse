"""
User Activities sync engine for SalesPro
"""
import logging
from typing import Dict, Any, List
from .base import SalesProBaseSyncEngine
from ..clients import UserActivitiesClient

logger = logging.getLogger(__name__)

class UserActivitiesSyncEngine(SalesProBaseSyncEngine):
    """Sync engine for SalesPro user activities"""
    
    def __init__(self, **kwargs):
        super().__init__('useractivities', **kwargs)
        
    async def initialize_client(self) -> None:
        """Initialize user activities client"""
        self.client = UserActivitiesClient()
        await self.client.authenticate()
        logger.info("User Activities client initialized")
        
    async def initialize_processor(self) -> None:
        """Initialize user activities processor"""
        from ingestion.models.salespro import SalesPro_UserActivity
        from ..processors.base import SalesProBaseProcessor
        self.processor = SalesProBaseProcessor(SalesPro_UserActivity)
        logger.info("User Activities processor initialized")
        
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch user activities data"""
        since_date = kwargs.get('since_date')
        limit = kwargs.get('max_records', 0)
        
        logger.info(f"Fetching user activities data (since: {since_date}, limit: {limit})")
        data = await self.client.get_user_activities(since_date=since_date, limit=limit)
        logger.info(f"Fetched {len(data)} user activities records")
        
        return data
