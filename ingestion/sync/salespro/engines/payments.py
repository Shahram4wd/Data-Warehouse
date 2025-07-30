"""
Payments sync engine for SalesPro
"""
import logging
from typing import Dict, Any, List
from .base import SalesProBaseSyncEngine
from ..clients import PaymentsClient

logger = logging.getLogger(__name__)

class PaymentsSyncEngine(SalesProBaseSyncEngine):
    """Sync engine for SalesPro payments"""
    
    def __init__(self, **kwargs):
        super().__init__('payments', **kwargs)
        
    async def initialize_client(self) -> None:
        """Initialize payments client"""
        self.client = PaymentsClient()
        await self.client.authenticate()
        logger.info("Payments client initialized")
        
    async def initialize_processor(self) -> None:
        """Initialize payments processor"""
        from ingestion.models.salespro import SalesPro_Payment
        from ..processors.base import SalesProBaseProcessor
        self.processor = SalesProBaseProcessor(SalesPro_Payment)
        logger.info("Payments processor initialized")
        
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch payments data"""
        since_date = kwargs.get('since_date')
        limit = kwargs.get('max_records', 0)
        
        logger.info(f"Fetching payments data (since: {since_date}, limit: {limit})")
        data = await self.client.get_payments(since_date=since_date, limit=limit)
        logger.info(f"Fetched {len(data)} payments records")
        
        return data
