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
        
        # Base query with all required fields
        query = """
        SELECT 
            at.id,
            at.label as name,
            '' as code,
            '' as description,
            0 as duration_minutes,
            '' as color,
            at.is_active as active,
            at.id as sort_order,
            NOW() as created_at,
            NOW() as updated_at
        FROM appointment_type at
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY at.id"
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
            'description',
            'duration_minutes',
            'color',
            'active',
            'sort_order',
            'created_at',
            'updated_at'
        ]
