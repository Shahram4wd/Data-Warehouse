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
    
    def get_chunked_jobs(self, offset: int, chunk_size: int, since_date: Optional[datetime] = None) -> List[tuple]:
        """Fetch jobs data in chunks for large datasets"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
        query = f"""
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
            j.service_id
        FROM {self.table_name} j
        """
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" ORDER BY j.id LIMIT {chunk_size} OFFSET {offset}"
        return self.execute_query(query)

    def get_chunked_query(self, offset: int, chunk_size: int, since_date: Optional[datetime] = None) -> str:
        """Get the chunked query for logging purposes"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
        query = f"""
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
            j.service_id
        FROM {self.table_name} j
        """
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" ORDER BY j.id LIMIT {chunk_size} OFFSET {offset}"
        return query
    
    def get_field_mapping(self) -> Dict[str, int]:
        """Return field mapping for processor (field_name -> column_index)"""
        return {
            'id': 0,
            'prospect_id': 1,
            'division_id': 2,
            'status': 3,
            'contract_amount': 4,
            'start_date': 5,
            'end_date': 6,
            'add_user_id': 7,
            'add_date': 8,
            'updated_at': 9,
            'service_id': 10
        }
