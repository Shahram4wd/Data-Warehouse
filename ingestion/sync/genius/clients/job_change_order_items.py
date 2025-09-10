"""
Job Change Order Items client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderItemClient(GeniusBaseClient):
    """Client for accessing Genius CRM job change order item data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'job_change_order_item'
    
    def get_job_change_order_items(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch job change order items from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT *
        FROM job_change_order_item jcoi
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY jcoi.Id"
        if limit and limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'change_order_id',
            'description', 
            'amount',
            'created_at',
            'updated_at'
        ]
