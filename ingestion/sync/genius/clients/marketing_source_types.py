"""
Marketing Source Type client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusMarketingSourceTypeClient(GeniusBaseClient):
    """Client for accessing Genius CRM marketing source type data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'marketing_source_type'
    
    def get_marketing_source_types(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch marketing source types from Genius database"""
        
        # Base query with all required fields matching the model
        query = """
        SELECT 
            mst.id,
            mst.label,
            mst.description,
            mst.is_active,
            mst.list_order,
            mst.created_at,
            mst.updated_at
        FROM `marketing_source_type` mst
        """
        
        # Add WHERE clause for incremental sync - handle both updated_at and created_at
        if since_date:
            since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
            query += f" WHERE (mst.updated_at > '{since_str}' OR (mst.updated_at IS NULL AND mst.created_at > '{since_str}'))"
        
        # Add ordering and limit
        query += " ORDER BY mst.list_order, mst.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'label', 
            'description',
            'is_active',
            'list_order',
            'created_at',
            'updated_at'
        ]
    
    def get_marketing_source_types_chunked(self, since_date: Optional[datetime] = None, chunk_size: int = 1000):
        """Generator that yields chunks of marketing source types to handle large datasets efficiently"""
        offset = 0
        
        while True:
            # Base query with all required fields matching the model
            query = """
            SELECT 
                mst.id,
                mst.label,
                mst.description,
                mst.is_active,
                mst.list_order,
                mst.created_at,
                mst.updated_at
            FROM `marketing_source_type` mst
            """
            
            # Add WHERE clause for incremental sync - handle both updated_at and created_at
            if since_date:
                since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
                query += f" WHERE (mst.updated_at > '{since_str}' OR (mst.updated_at IS NULL AND mst.created_at > '{since_str}'))"
            
            # Add ordering and pagination
            query += f" ORDER BY mst.id LIMIT {chunk_size} OFFSET {offset}"
            
            logger.info(f"Executing chunked query (offset: {offset}, chunk_size: {chunk_size})")
            chunk_results = self.execute_query(query)
            
            if not chunk_results:
                # No more records, break the loop
                break
            
            yield chunk_results
            
            # If we got less than chunk_size records, we've reached the end
            if len(chunk_results) < chunk_size:
                break
            
            offset += chunk_size
