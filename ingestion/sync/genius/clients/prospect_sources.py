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
        
        # Base query with all required fields
        query = """
        SELECT 
            ps.id,
            ps.name,
            ps.code,
            ps.description,
            ps.marketing_source_id,
            ps.active,
            ps.sort_order,
            ps.created_at,
            ps.updated_at
        FROM prospect_source ps
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY ps.sort_order, ps.id"
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
            'marketing_source_id',
            'active',
            'sort_order',
            'created_at',
            'updated_at'
        ]
