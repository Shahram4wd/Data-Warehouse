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
            mmsm.id,
            mmsm.marketsharp_source_id,
            mmsm.marketing_source_id,
            mmsm.prospect_source_id,
            mmsm.priority,
            mmsm.active,
            mmsm.created_at,
            mmsm.updated_at
        FROM marketsharp_marketing_source_map mmsm
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY mmsm.priority, mmsm.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'marketsharp_source_id',
            'marketing_source_id',
            'prospect_source_id',
            'priority',
            'active',
            'created_at',
            'updated_at'
        ]
