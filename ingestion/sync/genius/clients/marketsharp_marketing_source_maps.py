"""
MarketSharp Marketing Source Map client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusMarketSharpMarketingSourceMapClient(GeniusBaseClient):
    """Client for accessing Genius CRM MarketSharp marketing source map data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'marketsharp_marketing_source_map'
    
    def get_marketsharp_marketing_source_maps(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch MarketSharp marketing source maps from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            mmsm.marketsharp_id,
            mmsm.marketing_source_id,
            mmsm.created_at,
            mmsm.updated_at
        FROM marketsharp_marketing_source_map mmsm
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY mmsm.marketsharp_id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_marketsharp_marketing_source_maps_chunked(self, since_date: Optional[datetime] = None, chunk_size: int = 1000):
        """Generator that yields chunks of marketsharp marketing source maps to handle large datasets efficiently"""
        offset = 0
        
        while True:
            # Base query with all required fields
            query = """
            SELECT 
                mmsm.marketsharp_id,
                mmsm.marketing_source_id,
                mmsm.created_at,
                mmsm.updated_at
            FROM marketsharp_marketing_source_map mmsm
            """
            
            # Add WHERE clause for incremental sync
            where_clause = self.build_where_clause(since_date, self.table_name)
            if where_clause:
                query += f" {where_clause}"
            
            # Add ordering and pagination
            query += f" ORDER BY mmsm.marketsharp_id LIMIT {chunk_size} OFFSET {offset}"
            
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
            'marketsharp_id',
            'marketing_source_id',
            'created_at',
            'updated_at'
        ]
