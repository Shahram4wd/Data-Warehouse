"""
Marketing Source client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusMarketingSourceClient(GeniusBaseClient):
    """Client for accessing Genius CRM marketing source data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'marketing_source'
    
    def get_marketing_sources(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch marketing sources from Genius database"""
        
        # Base query with all required fields that match the actual database structure
        query = """
        SELECT 
            ms.id,
            ms.type_id,
            ms.label,
            ms.description,
            ms.start_date,
            ms.end_date,
            ms.add_user_id,
            ms.add_date,
            ms.is_active,
            ms.is_allow_lead_modification,
            ms.updated_at
        FROM marketing_source ms
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit (using fields that actually exist)
        query += " ORDER BY ms.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'type_id',
            'label',
            'description',
            'start_date',
            'end_date',
            'add_user_id',
            'add_date',
            'is_active',
            'is_allow_lead_modification',
            'updated_at'
        ]
