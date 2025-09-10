"""
Job Change Order Reasons client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderReasonClient(GeniusBaseClient):
    """Client for accessing Genius CRM job change order reason data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'job_change_order_reason'
    
    def get_job_change_order_reasons(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch job change order reasons from Genius database
        
        Note: This table does not have updated_at field, so delta sync is not supported.
        Always performs full sync regardless of since_date parameter.
        """
        
        # Base query with all required fields  
        query = """
        SELECT *
        FROM job_change_order_reason jcor
        """
        
        # Note: No WHERE clause for since_date as this table has no timestamp fields
        # This is a lookup table that should be fully synced each time
        
        # Add ordering and limit
        query += " ORDER BY jcor.Id"
        if limit and limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'label',
            'description'
        ]
