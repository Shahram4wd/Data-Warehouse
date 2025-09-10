"""
Appointment Type client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusAppointmentTypeClient(GeniusBaseClient):
    """Client for accessing Genius CRM appointment type data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'appointment_type'
    
    def get_appointment_types(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch appointment types from Genius database"""
        
        # Base query selecting all fields from appointment_type table
        query = "SELECT * FROM appointment_type"
        
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
        """Get field mapping for transformation - matches actual database columns"""
        return [
            'id',
            'label',
            'is_active'
        ]
