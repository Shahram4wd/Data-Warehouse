"""
Division Group client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusDivisionGroupClient(GeniusBaseClient):
    """Client for accessing Genius CRM division group data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'division_group'
    
    def get_division_groups(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch division groups from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            dg.id,
            dg.group_label as name,
            dg.region as code,
            dg.is_active as active,
            dg.created_at,
            dg.updated_at
        FROM division_group dg
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY dg.id"
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
            'active',
            'created_at',
            'updated_at'
        ]
