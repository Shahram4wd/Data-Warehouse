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
        """Fetch appointment outcome types from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            aot.id,
            aot.name,
            aot.code,
            aot.description,
            aot.active,
            aot.sort_order,
            aot.created_at,
            aot.updated_at
        FROM appointment_outcome_type aot
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY aot.sort_order, aot.id"
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
            'active',
            'sort_order',
            'created_at',
            'updated_at'
        ]
