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
        
        # Base query with all available fields
        query = """
        SELECT 
            jco.id,
            jco.job_id,
            jco.number,
            jco.status_id,
            jco.type_id,
            jco.adjustment_change_order_id,
            jco.effective_date,
            jco.total_amount,
            jco.add_user_id,
            jco.add_date,
            jco.sold_user_id,
            jco.sold_date,
            jco.cancel_user_id,
            jco.cancel_date,
            jco.reason_id,
            jco.envelope_id,
            jco.total_contract_amount,
            jco.total_pre_change_orders_amount,
            jco.signer_name,
            jco.signer_email,
            jco.financing_note,
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
            'number',
            'status_id',
            'type_id',
            'adjustment_change_order_id',
            'effective_date',
            'total_amount',
            'add_user_id',
            'add_date',
            'sold_user_id',
            'sold_date',
            'cancel_user_id',
            'cancel_date',
            'reason_id',
            'envelope_id',
            'total_contract_amount',
            'total_pre_change_orders_amount',
            'signer_name',
            'signer_email',
            'financing_note',
            'updated_at'
        ]
