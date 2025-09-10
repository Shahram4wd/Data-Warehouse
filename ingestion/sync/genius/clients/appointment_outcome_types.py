"""
Appointment Outcome Type client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusAppointmentOutcomeTypeClient(GeniusBaseClient):
    """Client for accessing Genius CRM appointment outcome type data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'appointment_outcome_type'
    
    def get_appointment_outcome_types(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch appointment outcome types from Genius database - select all fields with delta support"""
        
        # Simple query to get all fields from the table
        query = "SELECT * FROM appointment_outcome_type"
        
        # Add WHERE clause for incremental sync if needed
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering
        query += " ORDER BY id"
        
        # Add limit if specified
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation - matches actual database table structure"""
        return [
            'id',
            'label',
            'sort_idx',
            'is_active',
            'created_at',
            'updated_at'
        ]
