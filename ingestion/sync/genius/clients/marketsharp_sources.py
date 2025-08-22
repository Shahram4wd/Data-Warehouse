"""
MarketSharp Source client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusMarketSharpSourceClient(GeniusBaseClient):
    """Client for accessing Genius CRM MarketSharp source data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'marketsharp_source'
    
    def get_marketsharp_sources(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch MarketSharp sources from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            mss.id,
            mss.name,
            mss.code,
            mss.description,
            mss.marketsharp_id,
            mss.active,
            mss.sort_order,
            mss.created_at,
            mss.updated_at
        FROM marketsharp_source mss
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY mss.sort_order, mss.id"
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
            'description',
            'marketsharp_id',
            'active',
            'sort_order',
            'created_at',
            'updated_at'
        ]
