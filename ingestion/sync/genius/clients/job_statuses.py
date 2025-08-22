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
            js.name,
            js.code,
            js.active,
            js.sort_order,
            js.created_at,
            js.updated_at
        FROM job_status js
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY js.sort_order, js.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'name',
            'code',
            'active',
            'sort_order',
            'created_at',
            'updated_at'
        ]
