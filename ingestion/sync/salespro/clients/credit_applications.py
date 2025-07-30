"""
Credit Applications Athena client for SalesPro
"""
import logging
from typing import Dict, Any, List, Optional
from .base import SalesProBaseClient

logger = logging.getLogger(__name__)

class CreditApplicationsClient(SalesProBaseClient):
    """Athena client for SalesPro credit_applications table operations"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.table_name = 'credit_applications'
    
    async def get_credit_applications(self, since_date: Optional[str] = None, limit: int = 0) -> List[Dict[str, Any]]:
        """Get credit applications from Athena with optional filtering"""
        query = f"SELECT * FROM {self.table_name}"
        
        conditions = []
        if since_date:
            # Credit applications table uses updated_at for filtering
            conditions.append(f"updated_at > timestamp '{since_date}'")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY updated_at"
        
        if limit > 0:
            query += f" LIMIT {limit}"
        
        return await self.execute_query(query)
    
    async def get_credit_applications_count(self, since_date: Optional[str] = None) -> int:
        """Get count of credit applications with optional filtering"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at > timestamp '{since_date}'"
        
        return await self.get_table_count(self.table_name, where_clause)
