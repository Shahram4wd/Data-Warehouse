"""
Lead Results sync engine for SalesPro
"""
import logging
from typing import Dict, Any, List
from .base import SalesProBaseSyncEngine
from ..clients import LeadResultsClient
from ..processors.lead_result import SalesProLeadResultProcessor

logger = logging.getLogger(__name__)

class LeadResultsSyncEngine(SalesProBaseSyncEngine):
    """Sync engine for SalesPro lead results"""
    
    def __init__(self, **kwargs):
        super().__init__('leadresults', **kwargs)
        
    async def initialize_client(self) -> None:
        """Initialize lead results client"""
        self.client = LeadResultsClient()
        await self.client.authenticate()
        logger.info("Lead Results client initialized")
        
    async def initialize_processor(self) -> None:
        """Initialize lead results processor"""
        from ingestion.models.salespro import SalesPro_LeadResult
        self.processor = SalesProLeadResultProcessor(model_class=SalesPro_LeadResult)
        logger.info("Lead Results processor initialized")
        
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch lead results data"""
        since_date = kwargs.get('since_date')
        limit = kwargs.get('max_records', 0)
        
        logger.info(f"Fetching lead results data (since: {since_date}, limit: {limit})")
        data = await self.client.get_lead_results(since_date=since_date, limit=limit)
        logger.info(f"Fetched {len(data)} lead results records")
        
        return data
