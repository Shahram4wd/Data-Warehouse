"""
Quote client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusQuoteClient(GeniusBaseClient):
    """Client for accessing Genius CRM quote data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'quote'
    
    def get_quotes(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch quotes from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            q.id,
            q.prospect_id,
            q.user_id,
            q.division_id,
            q.quote_number,
            q.quote_date,
            q.total_amount,
            q.status,
            q.notes,
            q.valid_until,
            q.converted_to_job_id,
            q.created_at,
            q.updated_at
        FROM quote q
        """
        
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
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'prospect_id',
            'user_id',
            'division_id',
            'quote_number',
            'quote_date',
            'total_amount',
            'status',
            'notes',
            'valid_until',
            'converted_to_job_id',
            'created_at',
            'updated_at'
        ]
