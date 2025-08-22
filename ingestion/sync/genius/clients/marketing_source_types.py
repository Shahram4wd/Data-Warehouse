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
        
        # Base query with all required fields
        query = """
        SELECT 
            mst.id,
            mst.name,
            mst.code,
            mst.description,
            mst.active,
            mst.sort_order,
            mst.created_at,
            mst.updated_at
        FROM marketing_source_type mst
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY mst.sort_order, mst.id"
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
            'active',
            'sort_order',
            'created_at',
            'updated_at'
        ]
