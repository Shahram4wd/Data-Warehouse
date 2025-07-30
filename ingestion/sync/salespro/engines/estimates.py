"""
Estimates sync engine for SalesPro
"""
import logging
from typing import Dict, Any, List
from .base import SalesProBaseSyncEngine
from ..clients import EstimatesClient

logger = logging.getLogger(__name__)

class EstimatesSyncEngine(SalesProBaseSyncEngine):
    """Sync engine for SalesPro estimates"""
    
    def __init__(self, **kwargs):
        super().__init__('estimate', **kwargs)
        
    async def initialize_client(self) -> None:
        """Initialize estimates client"""
        self.client = EstimatesClient()
        await self.client.authenticate()
        logger.info("Estimates client initialized")
        
    async def initialize_processor(self) -> None:
        """Initialize estimates processor"""
        from ingestion.models.salespro import SalesPro_Estimate
        from ..processors.base import SalesProBaseProcessor
        self.processor = SalesProBaseProcessor(SalesPro_Estimate)
        logger.info("Estimates processor initialized")
        
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch estimates data"""
        since_date = kwargs.get('since_date')
        limit = kwargs.get('max_records', 0)
        
        logger.info(f"Fetching estimates data (since: {since_date}, limit: {limit})")
        data = await self.client.get_estimates(since_date=since_date, limit=limit)
        logger.info(f"Fetched {len(data)} estimates records")
        
        return data
