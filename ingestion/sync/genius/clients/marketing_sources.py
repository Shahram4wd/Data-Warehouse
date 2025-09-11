"""
Marketing Source client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusMarketingSourceClient(GeniusBaseClient):
    """Client for accessing Genius CRM marketing source data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'marketing_source'
    
    def get_marketing_sources(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch marketing sources from Genius database"""
        
        # Base query with all required fields that match the actual database structure
        query = """
        SELECT 
            ms.id,
            ms.type_id,
            ms.label,
            ms.description,
            ms.start_date,
            ms.end_date,
            ms.add_user_id,
            ms.add_date,
            ms.is_active,
            ms.is_allow_lead_modification,
            ms.updated_at
        FROM marketing_source ms
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit (using fields that actually exist)
        query += " ORDER BY ms.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_marketing_sources_chunked(self, since_date: Optional[datetime] = None, chunk_size: int = 1000):
        """Generator that yields chunks of marketing sources to handle large datasets efficiently"""
        offset = 0
        
        while True:
            # Base query with all required fields that match the actual database structure
            query = """
            SELECT 
                ms.id,
                ms.type_id,
                ms.label,
                ms.description,
                ms.start_date,
                ms.end_date,
                ms.add_user_id,
                ms.add_date,
                ms.is_active,
                ms.is_allow_lead_modification,
                ms.updated_at
            FROM marketing_source ms
            """
            
            # Add WHERE clause for incremental sync
            where_clause = self.build_where_clause(since_date, self.table_name)
            if where_clause:
                query += f" {where_clause}"
            
            # Add ordering and pagination
            query += f" ORDER BY ms.id LIMIT {chunk_size} OFFSET {offset}"
            
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
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'type_id',
            'label',
            'description',
            'start_date',
            'end_date',
            'add_user_id',
            'add_date',
            'is_active',
            'is_allow_lead_modification',
            'updated_at'
        ]
