"""
Job client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusJobClient(GeniusBaseClient):
    """Client for accessing Genius CRM job data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'job'
    
    def get_jobs(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch jobs from Genius database"""
        
        # Base query with core fields that exist in the database
        query = """
        SELECT
            j.id,
            j.prospect_id,
            j.division_id,
            j.status,
            j.contract_amount,
            j.start_date,
            j.end_date,
            j.add_user_id,
            j.add_date,
            j.updated_at,
            COALESCE(j.service_id, 8) as service_id
        FROM job j
        """        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY j.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'prospect_id',
            'division_id',
            'status',
            'contract_amount',
            'start_date',
            'end_date',
            'add_user_id',
            'add_date',
            'updated_at',
            'service_id'
        ]
