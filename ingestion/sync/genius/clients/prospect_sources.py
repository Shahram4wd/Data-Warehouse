"""
Prospect Source client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusProspectSourceClient(GeniusBaseClient):
    """Client for accessing Genius CRM prospect source data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'prospect_source'
    
    def get_prospect_sources(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch prospect sources from Genius database"""
        
        # Base query with all required fields matching the model schema
        query = """
        SELECT 
            ps.id,
            ps.prospect_id,
            ps.marketing_source_id,
            ps.source_date,
            ps.notes,
            ps.add_user_id,
            ps.add_date,
            ps.updated_at
        FROM prospect_source ps
        """
        
        # Add WHERE clause for incremental sync - handle both updated_at and add_date
        if since_date:
            since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
            query += f" WHERE (ps.updated_at > '{since_str}' OR (ps.updated_at IS NULL AND ps.add_date > '{since_str}'))"
        
        # Add ordering and limit
        query += " ORDER BY ps.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_prospect_sources_chunked(self, since_date: Optional[datetime] = None, chunk_size: int = 1000):
        """Generator that yields chunks of prospect sources to handle large datasets efficiently"""
        offset = 0
        
        while True:
            # Base query with all required fields matching the model schema
            query = """
            SELECT 
                ps.id,
                ps.prospect_id,
                ps.marketing_source_id,
                ps.source_date,
                ps.notes,
                ps.add_user_id,
                ps.add_date,
                ps.updated_at
            FROM prospect_source ps
            """
            
            # Add WHERE clause for incremental sync - handle both updated_at and add_date
            if since_date:
                since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
                query += f" WHERE (ps.updated_at > '{since_str}' OR (ps.updated_at IS NULL AND ps.add_date > '{since_str}'))"
            
            # Add ordering and pagination
            query += f" ORDER BY ps.id LIMIT {chunk_size} OFFSET {offset}"
            
            logger.info(f"Executing chunked query (offset: {offset}, chunk_size: {chunk_size}): {query}")
            chunk_results = self.execute_query(query)
            
            if not chunk_results:
                # No more records, break the loop
                break
            
            yield chunk_results
            
            # If we got less than chunk_size records, we've reached the end
            if len(chunk_results) < chunk_size:
                break
            
            offset += chunk_size
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation matching the model schema"""
        return [
            'id',
            'prospect_id',
            'marketing_source_id',
            'source_date',
            'notes',
            'add_user_id',
            'add_date',
            'updated_at'
        ]
