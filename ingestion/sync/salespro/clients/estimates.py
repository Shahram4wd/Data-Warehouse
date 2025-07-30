"""
Estimates Athena client for SalesPro
"""
import logging
from typing import Dict, Any, List, Optional
from .base import SalesProBaseClient

logger = logging.getLogger(__name__)

class EstimatesClient(SalesProBaseClient):
    """Athena client for SalesPro estimate table operations"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.table_name = 'estimate'
    
    async def get_estimates(self, since_date: Optional[str] = None, limit: int = 0) -> List[Dict[str, Any]]:
        """Get estimates from Athena with optional filtering"""
        query = f"SELECT * FROM {self.table_name}"
        
        conditions = []
        if since_date:
            # Estimate table uses updated_at for filtering
            conditions.append(f"updated_at > timestamp '{since_date}'")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY updated_at"
        
        if limit > 0:
            query += f" LIMIT {limit}"
        
        return await self.execute_query(query)
    
    async def get_estimates_count(self, since_date: Optional[str] = None) -> int:
        """Get count of estimates with optional filtering"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at > timestamp '{since_date}'"
        
        return await self.get_table_count(self.table_name, where_clause)
