"""
MarketSharp Appointment client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusMarketSharpAppointmentClient(GeniusBaseClient):
    """Client for accessing Genius CRM MarketSharp appointment data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'marketsharp_appointments'
    
    def get_marketsharp_appointments(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch MarketSharp appointments from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            ma.id,
            ma.external_id,
            ma.contact_id,
            ma.appointment_date,
            ma.appointment_time,
            ma.appointment_type_id,
            ma.salesperson_id,
            ma.lead_source,
            ma.marketing_source_id,
            ma.appointment_status,
            ma.outcome_id,
            ma.notes,
            ma.follow_up_date,
            ma.active,
            ma.created_at,
            ma.updated_at
        FROM marketsharp_appointments ma
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY ma.appointment_date DESC, ma.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'external_id',
            'contact_id',
            'appointment_date',
            'appointment_time',
            'appointment_type_id',
            'salesperson_id',
            'lead_source',
            'marketing_source_id',
            'appointment_status',
            'outcome_id',
            'notes',
            'follow_up_date',
            'active',
            'created_at',
            'updated_at'
        ]
