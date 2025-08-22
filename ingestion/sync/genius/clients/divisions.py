"""
Division client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusDivisionClient(GeniusBaseClient):
    """Client for accessing Genius CRM division data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'division'
    
    def get_divisions(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch divisions from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            d.id,
            d.group_id,
            d.region_id,
            d.label,
            d.abbreviation,
            d.is_utility,
            d.is_corp,
            d.is_omniscient,
            d.is_inactive,
            d.account_scheduler_id,
            d.created_at,
            d.updated_at
        FROM division d
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY d.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'group_id',
            'region_id',
            'label',
            'abbreviation',
            'is_utility',
            'is_corp',
            'is_omniscient',
            'is_inactive',
            'account_scheduler_id',
            'created_at',
            'updated_at'
        ]
