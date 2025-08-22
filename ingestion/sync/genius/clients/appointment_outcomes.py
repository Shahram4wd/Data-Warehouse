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
        
        # Base query with all required fields
        query = """
        SELECT 
            ao.id,
            ao.name,
            ao.code,
            ao.description,
            ao.outcome_type_id,
            ao.active,
            ao.sort_order,
            ao.created_at,
            ao.updated_at
        FROM appointment_outcome ao
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY ao.sort_order, ao.id"
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
            'outcome_type_id',
            'active',
            'sort_order',
            'created_at',
            'updated_at'
        ]
