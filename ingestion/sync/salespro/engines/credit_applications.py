"""
Credit Applications sync engine for SalesPro
"""
import logging
from typing import Dict, Any, List
from .base import SalesProBaseSyncEngine
from ..clients import CreditApplicationsClient

logger = logging.getLogger(__name__)

class CreditApplicationsSyncEngine(SalesProBaseSyncEngine):
    """Sync engine for SalesPro credit applications"""
    
    def __init__(self, **kwargs):
        super().__init__('creditapplications', **kwargs)
        
    async def initialize_client(self) -> None:
        """Initialize credit applications client"""
        self.client = CreditApplicationsClient()
        await self.client.authenticate()
        logger.info("Credit Applications client initialized")
        
    async def initialize_processor(self) -> None:
        """Initialize credit applications processor"""
        from ingestion.models.salespro import SalesPro_CreditApplication
        from ..processors.base import SalesProBaseProcessor
        self.processor = SalesProBaseProcessor(SalesPro_CreditApplication)
        logger.info("Credit Applications processor initialized")
        
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch credit applications data"""
        since_date = kwargs.get('since_date')
        limit = kwargs.get('max_records', 0)
        
        logger.info(f"Fetching credit applications data (since: {since_date}, limit: {limit})")
        data = await self.client.get_credit_applications(since_date=since_date, limit=limit)
        logger.info(f"Fetched {len(data)} credit applications records")
        
        return data
