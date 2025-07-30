"""
Customer sync engine for SalesPro
"""
import logging
from typing import Dict, Any, List
from .base import SalesProBaseSyncEngine
from ..clients import CustomerClient

logger = logging.getLogger(__name__)

class CustomerSyncEngine(SalesProBaseSyncEngine):
    """Sync engine for SalesPro customers"""
    
    def __init__(self, **kwargs):
        super().__init__('customer', **kwargs)
        
    async def initialize_client(self) -> None:
        """Initialize customer client"""
        self.client = CustomerClient()
        await self.client.authenticate()
        logger.info("Customer client initialized")
        
    async def initialize_processor(self) -> None:
        """Initialize customer processor"""
        from ingestion.models.salespro import SalesPro_Customer
        from ..processors.base import SalesProBaseProcessor
        self.processor = SalesProBaseProcessor(SalesPro_Customer)
        logger.info("Customer processor initialized")
        
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch customer data"""
        since_date = kwargs.get('since_date')
        limit = kwargs.get('max_records', 0)
        
        logger.info(f"Fetching customer data (since: {since_date}, limit: {limit})")
        data = await self.client.get_customers(since_date=since_date, limit=limit)
        logger.info(f"Fetched {len(data)} customer records")
        
        return data
