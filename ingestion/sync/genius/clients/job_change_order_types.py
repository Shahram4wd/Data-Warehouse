"""
Job Change Order Types client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderTypeClient(GeniusBaseClient):
    """Client for accessing Genius CRM job change order type data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'job_change_order_type'
    
    def get_job_change_order_types(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch job change order types from Genius database
        
        Note: This table does not have updated_at field, so delta sync is not supported.
        Always performs full sync regardless of since_date parameter.
        """
        
        # Base query with all required fields  
        query = """
        SELECT 
            jcot.id,
            jcot.label
        FROM job_change_order_type jcot
        """
        
        # Add ordering and limit
        query += " ORDER BY jcot.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'label'
        ]

    def get_job_change_order_types_chunked(self, since_date: Optional[datetime] = None, chunk_size: int = 1000):
        """Generator that yields chunks of job change order types to handle large datasets efficiently
        
        Note: This table does not have updated_at field, so delta sync is not supported.
        Always performs full sync regardless of since_date parameter.
        """
        offset = 0
        
        while True:
            # Base query with all required fields
            query = """
            SELECT 
                jcot.id,
                jcot.label
            FROM job_change_order_type jcot
            """
            
            # Add ordering and pagination
            query += f" ORDER BY jcot.id LIMIT {chunk_size} OFFSET {offset}"
            
            logger.info(f"Executing chunked query (offset: {offset}, chunk_size: {chunk_size})")
            chunk_results = self.execute_query(query)
            
            if not chunk_results:
                # No more records, break the loop
                break
            
            yield chunk_results
            offset += chunk_size
            
            # If we got less than chunk_size records, we're at the end
            if len(chunk_results) < chunk_size:
                break