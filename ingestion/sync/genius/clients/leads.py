"""
Lead client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusLeadClient(GeniusBaseClient):
    """Client for accessing Genius CRM lead data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'lead'
    
    def get_leads(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch leads from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            l.id,
            l.first_name,
            l.last_name,
            l.email,
            l.phone,
            l.address,
            l.city,
            l.state,
            l.zip_code,
            l.prospect_source_id,
            l.user_id,
            l.division_id,
            l.notes,
            l.status,
            l.converted_to_prospect_id,
            l.created_at,
            l.updated_at
        FROM `lead` l
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY l.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'city',
            'state',
            'zip_code',
            'prospect_source_id',
            'user_id',
            'division_id',
            'notes',
            'status',
            'converted_to_prospect_id',
            'created_at',
            'updated_at'
        ]
