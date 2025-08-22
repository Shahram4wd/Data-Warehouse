"""
MarketSharp Contact client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusMarketSharpContactClient(GeniusBaseClient):
    """Client for accessing Genius CRM MarketSharp contact data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'marketsharp_contacts'
    
    def get_marketsharp_contacts(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch MarketSharp contacts from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            mc.id,
            mc.external_id,
            mc.first_name,
            mc.last_name,
            mc.email,
            mc.phone,
            mc.address_1,
            mc.address_2,
            mc.city,
            mc.state,
            mc.zip,
            mc.marketing_source_id,
            mc.prospect_source_id,
            mc.lead_status,
            mc.appointment_date,
            mc.appointment_time,
            mc.notes,
            mc.active,
            mc.created_at,
            mc.updated_at
        FROM marketsharp_contacts mc
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY mc.updated_at DESC, mc.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'external_id',
            'first_name',
            'last_name',
            'email',
            'phone',
            'address_1',
            'address_2',
            'city',
            'state',
            'zip',
            'marketing_source_id',
            'prospect_source_id',
            'lead_status',
            'appointment_date',
            'appointment_time',
            'notes',
            'active',
            'created_at',
            'updated_at'
        ]
