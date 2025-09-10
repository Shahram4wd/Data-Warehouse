"""
Job Status client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusJobStatusClient(GeniusBaseClient):
    """Client for accessing Genius CRM job status data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'job_status'
    
    def get_job_statuses(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch job statuses from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            js.id,
            js.label,
            js.is_system
        FROM job_status js
        """
        
        # Add WHERE clause for incremental sync (job_status is a lookup table, typically no timestamps)
        # Since job_status doesn't have timestamp fields, we'll do full syncs
        
        # Add ordering and limit
        query += " ORDER BY js.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'label',
            'is_system'
        ]
