"""
Job Change Order client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderClient(GeniusBaseClient):
    """Client for accessing Genius CRM job change order data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'job_change_order'
    
    def get_job_change_orders(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch job change orders from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            jco.id,
            jco.job_id,
            jco.change_order_number,
            jco.change_order_type_id,
            jco.change_order_status_id,
            jco.change_order_reason_id,
            jco.description,
            jco.amount,
            jco.requested_date,
            jco.approved_date,
            jco.completed_date,
            jco.requested_by_user_id,
            jco.approved_by_user_id,
            jco.notes,
            jco.created_at,
            jco.updated_at
        FROM job_change_order jco
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY jco.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'job_id',
            'change_order_number',
            'change_order_type_id',
            'change_order_status_id',
            'change_order_reason_id',
            'description',
            'amount',
            'requested_date',
            'approved_date',
            'completed_date',
            'requested_by_user_id',
            'approved_by_user_id',
            'notes',
            'created_at',
            'updated_at'
        ]
