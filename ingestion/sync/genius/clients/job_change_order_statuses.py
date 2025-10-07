"""
Job Change Order Statuses client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderStatusClient(GeniusBaseClient):
    """Client for accessing Genius CRM job change order status data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'job_change_order_status'
    
    def get_job_change_order_statuses(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch job change order statuses from Genius database
        
        Note: This table does not have updated_at field, so delta sync is not supported.
        Always performs full sync regardless of since_date parameter.
        """
        
        # Base query with all required fields  
        query = """
        SELECT 
            jcos.id,
            jcos.label,
            jcos.is_selectable
        FROM job_change_order_status jcos
        """
        
        # Add ordering and limit
        query += " ORDER BY jcos.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'label',
            'is_selectable'
        ]

    def get_job_change_order_statuses_chunked(self, since_date: Optional[datetime] = None, chunk_size: int = 1000):
        """Generator that yields chunks of job change order statuses to handle large datasets efficiently
        
        Args:
            since_date: Not used for this table (no timestamp fields)
            chunk_size: Number of records per chunk
            
        Yields:
            List of tuples containing job change order status data
        """
        offset = 0
        while True:
            query = f"""
            SELECT 
                jcos.id,
                jcos.label,
                jcos.is_selectable
            FROM job_change_order_status jcos
            ORDER BY jcos.id
            LIMIT {chunk_size} OFFSET {offset}
            """
            
            logger.info(f"Executing chunked query (offset: {offset}, chunk_size: {chunk_size})")
            chunk = self.execute_query(query)
            
            if not chunk:
                break
                
            yield chunk
            offset += chunk_size

    def count_records(self, since_date: Optional[datetime] = None) -> int:
        """Count total records available for sync"""
        query = "SELECT COUNT(*) FROM job_change_order_status"
        
        result = self.execute_query(query)
        return result[0][0] if result else 0