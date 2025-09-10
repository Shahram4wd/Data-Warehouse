"""
Appointment Outcome client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusAppointmentOutcomeClient(GeniusBaseClient):
    """Client for accessing Genius CRM appointment outcome data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'appointment_outcome'
    
    def get_appointment_outcomes(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch appointment outcomes from Genius database"""
        
        # Use SELECT * to get all available fields from the database
        query = "SELECT * FROM appointment_outcome"
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation - matches actual database fields"""
        return [
            'id',
            'type_id',
            'label',
            'is_active',
            'created_at',
            'updated_at'
        ]
