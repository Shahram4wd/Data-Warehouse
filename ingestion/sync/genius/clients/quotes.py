"""
Quote client for Genius CRM database access
Following CRM sync guide with chunked processing support
"""
import logging
from typing import Optional, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger('quotes')


class GeniusQuoteClient(GeniusBaseClient):
    """Client for accessing Genius CRM quote data with chunked processing"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'quote'
    
    def get_quotes(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch quotes from Genius database"""
        
        query = self._get_base_query()
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY q.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_chunked_quotes(self, since_date: Optional[datetime] = None, offset: int = 0, chunk_size: int = 100000) -> List[tuple]:
        """Fetch chunked quotes for large dataset processing"""
        
        query = self.get_chunked_query(since_date, offset, chunk_size)
        logger.info(query)
        return self.execute_query(query)
    
    def get_chunked_query(self, since_date: Optional[datetime] = None, offset: int = 0, chunk_size: int = 100000) -> str:
        """Build chunked query for large dataset processing"""
        
        query = self._get_base_query()
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and chunking
        query += f" ORDER BY q.id LIMIT {chunk_size} OFFSET {offset}"
        
        return query
    
    def _get_base_query(self) -> str:
        """Get the base query for quotes"""
        return """
            SELECT
                q.id,
                q.prospect_id,
                q.appointment_id,
                q.job_id,
                q.client_cid,
                q.service_id,
                q.label,
                q.description,
                q.amount,
                q.expire_date,
                q.status_id,
                q.contract_file_id,
                q.estimate_file_id,
                q.add_user_id,
                q.add_date,
                q.updated_at
            FROM quote q
        """
