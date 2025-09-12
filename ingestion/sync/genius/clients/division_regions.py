"""
Division Region client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusDivisionRegionClient(GeniusBaseClient):
    """Client for accessing Genius CRM division region data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'division_region'
    
    def get_division_regions(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch division regions from Genius database"""
        
        # Base query selecting all fields from division_region table
        query = "SELECT dr.* FROM division_region dr"
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY dr.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation - matches actual database columns"""
        return [
            'id',
            'name',
            'is_active'
        ]
